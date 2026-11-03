"""Composes the rule-based heuristics into ranked, persistable suggestion
dicts. This pass never calls the AI Core — it's the always-available,
zero-cost first layer of `OptimizationService.suggest()`. Ranking is
objective-aware: a QUALITY pass surfaces clarity/few-shot/formatting
issues first, while a COST/LATENCY/TOKEN_COUNT pass surfaces
compression/parameter issues first.
"""
from __future__ import annotations

from ai_core.registry.model_registry import ModelRegistry

from prompt_platform.domain.enums import OptimizationCategory, OptimizationObjective
from prompt_platform.prompt_optimization.heuristics import (
    COMPRESSION_TOKEN_THRESHOLD,
    EXPANSION_TOKEN_FLOOR,
    duplicate_whitespace_ratio,
    estimate_tokens,
    find_vague_terms,
    has_few_shot_examples,
    has_output_format_guidance,
    variable_usage_report,
)

_QUALITY_FIRST = [
    OptimizationCategory.INSTRUCTION_CLARITY, OptimizationCategory.FEW_SHOT_EXAMPLES,
    OptimizationCategory.RESPONSE_FORMATTING, OptimizationCategory.VARIABLE_USAGE,
    OptimizationCategory.EXPANSION, OptimizationCategory.COMPRESSION, OptimizationCategory.COST_LATENCY,
]
_EFFICIENCY_FIRST = [
    OptimizationCategory.COMPRESSION, OptimizationCategory.COST_LATENCY,
    OptimizationCategory.VARIABLE_USAGE, OptimizationCategory.INSTRUCTION_CLARITY,
    OptimizationCategory.RESPONSE_FORMATTING, OptimizationCategory.FEW_SHOT_EXAMPLES, OptimizationCategory.EXPANSION,
]


def _full_text(version) -> str:
    return "\n".join(filter(None, [version.system_template, version.developer_template, version.user_template]))


def generate_rule_based_suggestions(version, *, objective: OptimizationObjective, registry: ModelRegistry | None = None) -> list[dict]:
    text = _full_text(version)
    suggestions: list[dict] = []

    vague = find_vague_terms(text)
    if vague:
        suggestions.append({
            "category": OptimizationCategory.INSTRUCTION_CLARITY.value,
            "title": "Vague or unspecific language detected",
            "rationale": f"Found imprecise qualifiers that make instructions hard to follow consistently: {', '.join(vague)}.",
            "original_text": text, "suggested_text": None,
            "estimated_impact": {"vague_term_count": len(vague)},
        })

    if not has_output_format_guidance(version.user_template or ""):
        suggestions.append({
            "category": OptimizationCategory.RESPONSE_FORMATTING.value,
            "title": "No explicit output-format instructions",
            "rationale": "The template doesn't tell the model how to structure its response, which makes downstream parsing fragile.",
            "original_text": version.user_template, "suggested_text": None, "estimated_impact": None,
        })

    if not has_few_shot_examples(text):
        suggestions.append({
            "category": OptimizationCategory.FEW_SHOT_EXAMPLES.value,
            "title": "No few-shot examples present",
            "rationale": "Adding 1-3 worked examples from golden test cases typically improves consistency on ambiguous tasks.",
            "original_text": None, "suggested_text": None, "estimated_impact": None,
        })

    var_report = variable_usage_report(version)
    if var_report["unused_declared"] or var_report["undeclared_used"]:
        suggestions.append({
            "category": OptimizationCategory.VARIABLE_USAGE.value,
            "title": "Variable declaration mismatch",
            "rationale": (
                f"Declared but unused: {var_report['unused_declared'] or 'none'}. "
                f"Used but undeclared: {var_report['undeclared_used'] or 'none'}."
            ),
            "original_text": None, "suggested_text": None, "estimated_impact": var_report,
        })

    total_tokens = estimate_tokens(version.system_template, version.developer_template, version.user_template)
    if total_tokens > COMPRESSION_TOKEN_THRESHOLD:
        suggestions.append({
            "category": OptimizationCategory.COMPRESSION.value,
            "title": "Prompt is a compression candidate",
            "rationale": f"Estimated {total_tokens} tokens, above the {COMPRESSION_TOKEN_THRESHOLD}-token guideline. "
                         f"Redundant-whitespace ratio: {duplicate_whitespace_ratio(text):.2%}.",
            "original_text": text, "suggested_text": None,
            "estimated_impact": {"current_tokens": total_tokens},
        })
    elif total_tokens < EXPANSION_TOKEN_FLOOR:
        suggestions.append({
            "category": OptimizationCategory.EXPANSION.value,
            "title": "Prompt may be under-specified",
            "rationale": f"Estimated only {total_tokens} tokens — likely too terse to reliably constrain the model's behavior.",
            "original_text": text, "suggested_text": None,
            "estimated_impact": {"current_tokens": total_tokens},
        })

    if objective in (OptimizationObjective.COST, OptimizationObjective.LATENCY, OptimizationObjective.TOKEN_COUNT):
        params = version.parameters or {}
        notes = []
        if not params.get("max_tokens"):
            notes.append("no max_tokens cap set — uncapped generations risk runaway cost/latency")
        if registry is not None and params.get("model"):
            try:
                current = registry.get(params.get("provider", ""), params["model"])
                cheaper = [
                    m for m in registry.list_by_provider(current.provider)
                    if m.pricing.input_cost_per_1m < current.pricing.input_cost_per_1m and m.is_usable()
                ]
                if cheaper:
                    notes.append(f"a cheaper same-provider model is available: {cheaper[0].key}")
            except Exception:  # noqa: BLE001 — model lookup is best-effort advisory context
                pass
        if notes:
            suggestions.append({
                "category": OptimizationCategory.COST_LATENCY.value,
                "title": "Cost/latency tuning opportunities",
                "rationale": "; ".join(notes) + ".",
                "original_text": None, "suggested_text": None, "estimated_impact": {"total_tokens": total_tokens},
            })

    order = _EFFICIENCY_FIRST if objective in (
        OptimizationObjective.COST, OptimizationObjective.LATENCY, OptimizationObjective.TOKEN_COUNT
    ) else _QUALITY_FIRST
    rank = {c.value: i for i, c in enumerate(order)}
    suggestions.sort(key=lambda s: rank.get(s["category"], len(order)))
    return suggestions
