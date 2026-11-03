"""Live Preview / Token Estimator / Context Window Viewer / JSON Preview —
the read-only "what would this actually send to a model" view Prompt
Studio needs, computed without making a real model call.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ai_core.bootstrap import AICoreContext
from ai_core.prompts.composer import render_messages
from ai_core.prompts.template import PromptTemplate
from ai_core.schemas.enums import Role
from ai_core.schemas.requests import GenerationRequest
from ai_core.tokenizer.counter import count_message_tokens
from ai_core.utils.exceptions import NoAvailableModelError

from prompt_platform.core.exceptions import ValidationError


@dataclass
class ContextWindowUsage:
    provider: str | None
    model: str | None
    context_window: int | None
    used_tokens: int
    remaining_tokens: int | None
    percent_used: float | None


@dataclass
class PreviewResult:
    rendered_messages: list[dict] = field(default_factory=list)
    token_estimate: int = 0
    context_window: ContextWindowUsage | None = None
    json_preview: dict[str, Any] = field(default_factory=dict)


class PreviewService:
    def __init__(self, ai_core: AICoreContext):
        self.ai_core = ai_core

    def _build_templates(self, *, system_template, developer_template, user_template) -> list[PromptTemplate]:
        templates = []
        if system_template:
            templates.append(PromptTemplate(name="system", role=Role.SYSTEM, template=system_template))
        if developer_template:
            templates.append(PromptTemplate(name="developer", role=Role.DEVELOPER, template=developer_template))
        templates.append(PromptTemplate(name="user", role=Role.USER, template=user_template))
        return templates

    def render(
        self,
        *,
        system_template: str | None,
        developer_template: str | None,
        user_template: str,
        variables: dict,
        parameters: dict,
    ) -> PreviewResult:
        templates = self._build_templates(
            system_template=system_template, developer_template=developer_template, user_template=user_template
        )
        try:
            messages = render_messages(templates, variables)
        except Exception as exc:
            raise ValidationError(f"failed to render preview: {exc}") from exc

        model = parameters.get("model")
        provider = parameters.get("provider")
        token_estimate = count_message_tokens(messages, provider=provider or "openai", model=model or "gpt-4o")

        context_window = self._context_window_usage(provider=provider, model=model, used_tokens=token_estimate)

        request = GenerationRequest(
            messages=messages,
            model=model,
            provider=provider,
            temperature=parameters.get("temperature", 0.7),
            max_tokens=parameters.get("max_tokens"),
            response_format=parameters.get("response_format"),
        )
        json_preview = request.model_dump(mode="json", exclude_none=True)

        return PreviewResult(
            rendered_messages=[{"role": m.role.value, "content": m.text()} for m in messages],
            token_estimate=token_estimate,
            context_window=context_window,
            json_preview=json_preview,
        )

    def _context_window_usage(self, *, provider: str | None, model: str | None, used_tokens: int) -> ContextWindowUsage:
        candidate = None
        if provider and model:
            try:
                candidate = self.ai_core.registry.get(provider, model)
            except Exception:  # noqa: BLE001
                candidate = None
        elif model:
            matches = [m for m in self.ai_core.registry.all() if m.name == model]
            candidate = matches[0] if matches else None

        if candidate is None:
            # No specific model pinned — report against whatever the router
            # would pick by default, so the Studio still shows *something*
            # useful rather than blank fields.
            try:
                from ai_core.schemas.messages import ChatMessage
                from ai_core.schemas.requests import GenerationRequest as _GR

                chain = self.ai_core.router.route(_GR(messages=[ChatMessage(role=Role.USER, content="x")]))
                candidate = chain[0] if chain else None
            except NoAvailableModelError:
                candidate = None

        if candidate is None:
            return ContextWindowUsage(provider=provider, model=model, context_window=None, used_tokens=used_tokens, remaining_tokens=None, percent_used=None)

        remaining = max(candidate.context_window - used_tokens, 0)
        percent = round(used_tokens / candidate.context_window * 100, 2) if candidate.context_window else None
        return ContextWindowUsage(
            provider=candidate.provider, model=candidate.name, context_window=candidate.context_window,
            used_tokens=used_tokens, remaining_tokens=remaining, percent_used=percent,
        )
