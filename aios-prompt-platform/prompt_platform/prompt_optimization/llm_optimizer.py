"""LLM-backed prompt rewriting. Each function is a single, narrowly-scoped
generation call — plain text in, plain text out — so results are easy to
diff against the original and easy to script in tests. These are the
building blocks `OptimizationService.auto_optimize()` composes according
to the requested `OptimizationObjective`.
"""
from __future__ import annotations

from ai_core.bootstrap import AICoreContext
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest

_REWRITE_SYSTEM_PREAMBLE = (
    "You are an expert prompt engineer. You rewrite prompt templates for "
    "production LLM applications. Preserve every `{{variable}}` placeholder "
    "exactly as written — never rename, remove, or add placeholders. "
    "Return ONLY the rewritten template text, with no commentary, headers, "
    "or markdown code fences around it."
)


async def _rewrite(ai_core: AICoreContext, instruction: str, template: str, *, temperature: float = 0.3) -> str:
    request = GenerationRequest(
        messages=[
            ChatMessage(role=Role.SYSTEM, content=f"{_REWRITE_SYSTEM_PREAMBLE}\n\nTask: {instruction}"),
            ChatMessage(role=Role.USER, content=template),
        ],
        temperature=temperature,
    )
    response = await ai_core.execution_engine.generate(request)
    return response.content.strip()


async def refine_instructions(ai_core: AICoreContext, template: str) -> str:
    """Tightens vague or ambiguous instructions into explicit, unambiguous
    directives — the LLM-backed counterpart to `heuristics.find_vague_terms`."""
    return await _rewrite(
        ai_core,
        "Rewrite this prompt template so its instructions are explicit and unambiguous. "
        "Replace vague qualifiers (e.g. 'appropriate', 'good', 'properly') with concrete, "
        "checkable criteria. Keep the same overall intent and length class.",
        template,
    )


async def compress_prompt(ai_core: AICoreContext, template: str, *, target_ratio: float = 0.6) -> str:
    """Shortens the template while preserving intent and every variable
    placeholder — used for the COST/LATENCY/TOKEN_COUNT objectives."""
    pct = round((1 - target_ratio) * 100)
    return await _rewrite(
        ai_core,
        f"Compress this prompt template to roughly {pct}% shorter while preserving its full intent, "
        "constraints, and every {{variable}} placeholder. Remove redundancy and filler, not substance.",
        template,
        temperature=0.2,
    )


async def expand_prompt(ai_core: AICoreContext, template: str, *, focus: str | None = None) -> str:
    """Adds missing detail/context/constraints — used when a template is
    too terse to reliably guide the model (see `EXPANSION_TOKEN_FLOOR`)."""
    focus_clause = f" Focus especially on: {focus}." if focus else ""
    return await _rewrite(
        ai_core,
        "Expand this prompt template with clearer context, explicit constraints, and any missing "
        f"guidance a model would need to follow it reliably.{focus_clause} Keep every {{{{variable}}}} placeholder.",
        template,
    )


async def optimize_response_format(ai_core: AICoreContext, template: str, *, schema_hint: str | None = None) -> str:
    """Appends/rewrites explicit output-format instructions."""
    schema_clause = f" The required output shape is: {schema_hint}." if schema_hint else ""
    return await _rewrite(
        ai_core,
        "Add explicit, unambiguous output-format instructions to this prompt template so the model's "
        f"response is trivial to parse programmatically.{schema_clause} Keep every {{{{variable}}}} placeholder.",
        template,
    )
