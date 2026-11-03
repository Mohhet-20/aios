"""Orchestrates guardrail evaluation: runs the appropriate detector(s)
for the input's source, applies any tenant-configured custom rule
override (risk threshold + action) for the matched category, decides
allow/flag/block, and persists both the append-only evaluation log
entry and — for flag/block outcomes — a `GuardrailViolationModel`
record for follow-up. When the resolved action is BLOCK and
`guardrail_block_on_high_risk` is enabled, `GuardrailViolationError` is
raised *after* persisting the record, so the block is enforced but the
evidence trail is never lost even for a request that never completes."""
from __future__ import annotations

from collections.abc import Callable

from security_platform.config.settings import Settings, get_settings
from security_platform.core.exceptions import GuardrailViolationError, PromptTooLongError
from security_platform.domain.enums import GuardrailAction, GuardrailCategory
from security_platform.guardrails.detectors import (
    DetectionResult,
    detect_indirect_prompt_injection,
    detect_jailbreak,
    detect_prompt_injection,
    detect_unsafe_instruction,
)
from security_platform.guardrails.response_filter import filter_response
from security_platform.guardrails.validators import validate_structured_output
from security_platform.models.guardrails import GuardrailEvaluationModel, GuardrailViolationModel
from security_platform.repositories.registry import RepositoryRegistry

_INDIRECT_SOURCES = {"tool_output", "retrieved_document", "web"}


def _severity_for(risk_score: float) -> str:
    if risk_score >= 0.8:
        return "critical"
    if risk_score >= 0.6:
        return "high"
    if risk_score >= 0.4:
        return "medium"
    return "low"


class GuardrailService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    def _default_threshold(self, category: str) -> float:
        if category == GuardrailCategory.JAILBREAK.value:
            return self.settings.jailbreak_risk_threshold
        if category in (GuardrailCategory.PROMPT_INJECTION.value, GuardrailCategory.INDIRECT_PROMPT_INJECTION.value):
            return self.settings.prompt_injection_risk_threshold
        return 0.4  # unsafe_instruction and similar single-strong-signal categories

    async def _record_evaluation(
        self, tenant_id: str, *, category: str, input_excerpt: str, risk_score: float, action_taken: str,
        matched_rule_id: str | None, matched_signals: list[str], actor_id: str | None,
        resource_type: str | None, resource_id: str | None, context: dict | None = None,
    ) -> GuardrailEvaluationModel:
        evaluation = GuardrailEvaluationModel(
            tenant_id=tenant_id, category=category, input_excerpt=input_excerpt[:2000], risk_score=risk_score,
            action_taken=action_taken, matched_rule_id=matched_rule_id, matched_signals=matched_signals,
            context=context or {}, actor_id=actor_id, resource_type=resource_type, resource_id=resource_id,
        )
        evaluation = await self.repos.guardrail_evaluations.add(evaluation)
        if action_taken in (GuardrailAction.FLAG.value, GuardrailAction.BLOCK.value):
            await self.repos.guardrail_violations.add(
                GuardrailViolationModel(
                    tenant_id=tenant_id, evaluation_id=evaluation.id, category=category,
                    severity=_severity_for(risk_score), resource_type=resource_type, resource_id=resource_id, actor_id=actor_id,
                )
            )
        return evaluation

    async def evaluate_prompt(
        self,
        tenant_id: str,
        text: str,
        *,
        source: str = "user",
        actor_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
    ) -> GuardrailEvaluationModel:
        if len(text) > self.settings.max_prompt_length:
            raise PromptTooLongError(f"Prompt exceeds the maximum length of {self.settings.max_prompt_length} characters")

        # For content sourced from a tool, retrieved document, or the web,
        # the injection-pattern detector's signals are attributed to
        # INDIRECT_PROMPT_INJECTION instead of PROMPT_INJECTION — same
        # pattern set, but the source is what makes it "indirect" (see
        # detectors.py's docstring). Swap rather than add, so the two
        # categories never tie on score and race on detector order.
        injection_category = GuardrailCategory.INDIRECT_PROMPT_INJECTION if source in _INDIRECT_SOURCES else GuardrailCategory.PROMPT_INJECTION
        detectors: list[tuple[GuardrailCategory, Callable]] = [
            (injection_category, detect_indirect_prompt_injection if source in _INDIRECT_SOURCES else detect_prompt_injection),
            (GuardrailCategory.JAILBREAK, detect_jailbreak),
            (GuardrailCategory.UNSAFE_INSTRUCTION, detect_unsafe_instruction),
        ]

        best_category = GuardrailCategory.PROMPT_INJECTION
        best_result = DetectionResult(risk_score=0.0, signals=[])
        for category, detector_fn in detectors:
            result = detector_fn(text)
            if result.risk_score > best_result.risk_score:
                best_category, best_result = category, result

        rules = await self.repos.guardrail_rules.list_enabled_for_category(tenant_id, best_category.value)
        rule = rules[0] if rules else None
        threshold = rule.risk_threshold if rule else self._default_threshold(best_category.value)

        if best_result.risk_score >= threshold and best_result.signals:
            action = rule.action if rule else (
                GuardrailAction.BLOCK.value if self.settings.guardrail_block_on_high_risk else GuardrailAction.FLAG.value
            )
        else:
            action = GuardrailAction.ALLOW.value

        evaluation = await self._record_evaluation(
            tenant_id, category=best_category.value, input_excerpt=text, risk_score=best_result.risk_score,
            action_taken=action, matched_rule_id=rule.id if rule else None, matched_signals=best_result.signals,
            actor_id=actor_id, resource_type=resource_type, resource_id=resource_id, context={"source": source},
        )

        if action == GuardrailAction.BLOCK.value:
            raise GuardrailViolationError(
                f"Prompt blocked by guardrail category '{best_category.value}' (risk={best_result.risk_score:.2f}, "
                f"signals={best_result.signals})"
            )
        return evaluation

    async def validate_output(
        self, tenant_id: str, data, schema: dict, *, actor_id: str | None = None,
        resource_type: str | None = None, resource_id: str | None = None,
    ) -> tuple[GuardrailEvaluationModel, bool, list[str]]:
        result = validate_structured_output(data, schema)
        action = GuardrailAction.ALLOW.value if result.is_valid else GuardrailAction.FLAG.value
        evaluation = await self._record_evaluation(
            tenant_id, category=GuardrailCategory.STRUCTURED_OUTPUT_VALIDATION.value, input_excerpt=str(data),
            risk_score=0.0 if result.is_valid else 1.0, action_taken=action, matched_rule_id=None,
            matched_signals=result.errors, actor_id=actor_id, resource_type=resource_type, resource_id=resource_id,
        )
        return evaluation, result.is_valid, result.errors

    async def filter_response(
        self, tenant_id: str, text: str, banned_patterns: list[str], *, actor_id: str | None = None,
        resource_type: str | None = None, resource_id: str | None = None,
    ) -> tuple[GuardrailEvaluationModel, str]:
        result = filter_response(text, banned_patterns)
        action = GuardrailAction.ALLOW.value if result.redaction_count == 0 else GuardrailAction.REDACT.value
        evaluation = await self._record_evaluation(
            tenant_id, category=GuardrailCategory.RESPONSE_FILTER.value, input_excerpt=text,
            risk_score=1.0 if result.redaction_count else 0.0, action_taken=action, matched_rule_id=None,
            matched_signals=[f"{result.redaction_count} redaction(s)"], actor_id=actor_id,
            resource_type=resource_type, resource_id=resource_id,
        )
        return evaluation, result.filtered_text
