"""Tolerant JSON extraction from raw model output. Models routinely wrap
JSON in markdown code fences or add a sentence before/after it even when
asked not to — this parser accepts the realistic range of outputs instead
of requiring byte-perfect JSON."""
from __future__ import annotations

import json
import re

from ai_core.utils.exceptions import StructuredOutputError

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)
_BRACE_SPAN_RE = re.compile(r"\{.*\}|\[.*\]", re.DOTALL)


def extract_json_text(raw: str) -> str:
    text = raw.strip()
    fence_match = _FENCE_RE.search(text)
    if fence_match:
        return fence_match.group(1).strip()
    return text


def parse_json_response(raw: str) -> dict | list:
    candidate = extract_json_text(raw)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    # Last resort: the first/last brace-or-bracket span, in case the model
    # added prose around otherwise-valid JSON.
    span_match = _BRACE_SPAN_RE.search(candidate)
    if span_match:
        try:
            return json.loads(span_match.group(0))
        except json.JSONDecodeError as exc:
            raise StructuredOutputError(f"could not parse JSON from model output: {exc}") from exc
    raise StructuredOutputError(f"model output contained no parseable JSON: {raw[:200]!r}")
