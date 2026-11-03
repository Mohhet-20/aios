"""Deterministic, rule-based prompt analysis — no LLM call required. These
run instantly and for free, so `OptimizationService.suggest()` always
produces at least this pass; LLM-backed rewriting (llm_optimizer.py) is
layered on top only when the caller wants `auto_optimize`.
"""
from __future__ import annotations

import re

from ai_core.prompts.template import PromptTemplate
from ai_core.schemas.enums import Role
from ai_core.tokenizer.counter import count_tokens

_VAGUE_TERMS = [
    "somehow", "appropriate", "good", "nice", "properly", "correctly",
    "as needed", "etc", "and so on", "make it better", "if possible",
]
_FORMAT_HINTS = ["json", "format:", "respond with", "return only", "output format", "markdown", "bullet"]
_FEW_SHOT_MARKERS = ["example:", "example 1", "e.g.", "for instance", "### example", "input:", "output:"]

# A prompt whose rendered text alone exceeds this many tokens is flagged as
# a compression candidate; below this, expansion (more explicit guidance)
# tends to help quality more than trimming does.
COMPRESSION_TOKEN_THRESHOLD = 800
EXPANSION_TOKEN_FLOOR = 40


def find_vague_terms(text: str) -> list[str]:
    lowered = text.lower()
    return sorted({term for term in _VAGUE_TERMS if term in lowered})


def has_output_format_guidance(text: str) -> bool:
    lowered = text.lower()
    return any(hint in lowered for hint in _FORMAT_HINTS)


def has_few_shot_examples(text: str) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in _FEW_SHOT_MARKERS)


def estimate_tokens(*texts: str | None, provider: str = "openai", model: str = "gpt-4o") -> int:
    return sum(count_tokens(t or "", provider=provider, model=model) for t in texts)


def variable_usage_report(version) -> dict:
    """Compares the variables declared in `variables_schema` against the
    ones actually referenced (`{{name}}`) in the templates, using the AI
    Core's own placeholder parser so this stays consistent with what
    Studio's live-preview/validation uses."""
    declared = {v["name"] for v in (version.variables_schema or [])}
    used: set[str] = set()
    for role, template in (
        (Role.SYSTEM, version.system_template), (Role.DEVELOPER, version.developer_template), (Role.USER, version.user_template),
    ):
        if template:
            used |= set(PromptTemplate(name=role.value, role=role, template=template).required_variables)
    return {
        "declared": sorted(declared),
        "used": sorted(used),
        "unused_declared": sorted(declared - used),
        "undeclared_used": sorted(used - declared),
    }


def duplicate_whitespace_ratio(text: str) -> float:
    """Rough signal for compressibility: fraction of the text that is
    redundant whitespace/repeated punctuation, independent of token count."""
    if not text:
        return 0.0
    collapsed = re.sub(r"\s+", " ", text).strip()
    return round(1 - (len(collapsed) / max(len(text), 1)), 4)
