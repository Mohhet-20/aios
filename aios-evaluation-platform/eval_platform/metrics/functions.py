"""The 20 quality-metric compute functions. Every function reads only
from `MetricInput` and returns a genuinely-derived float — there is no
fabricated scoring anywhere here. A function raises
`MetricComputationError` when the signal it needs (an expected output,
a set of context documents, a latency sample, ...) simply was not
provided, rather than guessing. Several functions (groundedness,
faithfulness, citation_quality) use a lexical-overlap heuristic — the
same "genuinely computed, explicitly swappable for a stronger verifier
later" pattern used by the Tool Platform's `HallucinationCheckModel`."""
from __future__ import annotations

import json
import re

from eval_platform.core.exceptions import MetricComputationError
from eval_platform.metrics.inputs import MetricInput

_WORD_RE = re.compile(r"[a-z0-9]+")
_CITATION_RE = re.compile(r"\[(\d+)\]")


def _stringify(value) -> str:
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _tokens(value, *, min_len: int = 1) -> set[str]:
    return {tok for tok in _WORD_RE.findall(_stringify(value).lower()) if len(tok) >= min_len}


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _require(value, field_name: str):
    if value is None:
        raise MetricComputationError(f"cannot compute this metric without '{field_name}'")
    return value


# -- exact / set-overlap metrics ----------------------------------------------

def accuracy(i: MetricInput) -> float:
    _require(i.actual_output, "actual_output")
    _require(i.expected_output, "expected_output")
    a, e = _stringify(i.actual_output).strip().lower(), _stringify(i.expected_output).strip().lower()
    return 1.0 if a == e else 0.0


def precision(i: MetricInput) -> float:
    _require(i.actual_output, "actual_output")
    _require(i.expected_output, "expected_output")
    a_tokens, e_tokens = _tokens(i.actual_output), _tokens(i.expected_output)
    if not a_tokens:
        return 1.0 if not e_tokens else 0.0
    return len(a_tokens & e_tokens) / len(a_tokens)


def recall(i: MetricInput) -> float:
    _require(i.actual_output, "actual_output")
    _require(i.expected_output, "expected_output")
    a_tokens, e_tokens = _tokens(i.actual_output), _tokens(i.expected_output)
    if not e_tokens:
        return 1.0 if not a_tokens else 0.0
    return len(a_tokens & e_tokens) / len(e_tokens)


def f1_score(i: MetricInput) -> float:
    p, r = precision(i), recall(i)
    return 0.0 if (p + r) == 0 else 2 * p * r / (p + r)


# -- task / agent / workflow metrics ------------------------------------------

def task_success_rate(i: MetricInput) -> float:
    success = _require(i.success, "success")
    return 1.0 if success else 0.0


def reasoning_quality(i: MetricInput) -> float:
    _require(i.reasoning_steps, "reasoning_steps")
    _require(i.expected_reasoning_steps, "expected_reasoning_steps")
    return _jaccard(_tokens(" ".join(i.reasoning_steps)), _tokens(" ".join(i.expected_reasoning_steps)))


def planning_quality(i: MetricInput) -> float:
    _require(i.plan_steps, "plan_steps")
    _require(i.expected_plan_steps, "expected_plan_steps")
    return _jaccard(set(i.plan_steps), set(i.expected_plan_steps))


def reliability(i: MetricInput) -> float:
    success = _require(i.success, "success")
    base = 1.0 if success else 0.0
    retries = i.retry_count or 0
    if retries < 0:
        raise MetricComputationError("retry_count cannot be negative")
    return base / (1 + retries)


# -- groundedness / hallucination family ---------------------------------------

def groundedness(i: MetricInput) -> float:
    _require(i.actual_output, "actual_output")
    context = _require(i.context_documents, "context_documents")
    output_tokens = _tokens(i.actual_output, min_len=4)
    if not output_tokens:
        raise MetricComputationError("actual_output has no scorable content tokens")
    context_tokens = _tokens(" ".join(context), min_len=4)
    return len(output_tokens & context_tokens) / len(output_tokens)


def faithfulness(i: MetricInput) -> float:
    _require(i.actual_output, "actual_output")
    context = _require(i.context_documents, "context_documents")
    context_tokens = _tokens(" ".join(context), min_len=4)
    sentences = [s for s in re.split(r"[.!?]+", _stringify(i.actual_output)) if s.strip()]
    if not sentences:
        raise MetricComputationError("actual_output has no sentences to score")
    supported = 0
    for sentence in sentences:
        sentence_tokens = _tokens(sentence, min_len=4)
        if not sentence_tokens:
            continue
        overlap = len(sentence_tokens & context_tokens) / len(sentence_tokens)
        if overlap >= 0.5:
            supported += 1
    return supported / len(sentences)


def hallucination_rate(i: MetricInput) -> float:
    return 1.0 - groundedness(i)


def citation_quality(i: MetricInput) -> float:
    _require(i.actual_output, "actual_output")
    context = _require(i.context_documents, "context_documents")
    citations = _CITATION_RE.findall(_stringify(i.actual_output))
    if not citations:
        return 0.0
    valid = sum(1 for c in citations if 1 <= int(c) <= len(context))
    return valid / len(citations)


# -- output quality metrics -----------------------------------------------------

def response_completeness(i: MetricInput) -> float:
    return recall(i)


def instruction_following(i: MetricInput) -> float:
    _require(i.actual_output, "actual_output")
    instructions = _require(i.instructions, "instructions")
    if not instructions:
        raise MetricComputationError("instructions list is empty")
    output_tokens = _tokens(i.actual_output)
    satisfied = 0
    for instruction in instructions:
        instruction_tokens = _tokens(instruction, min_len=4)
        if not instruction_tokens or (instruction_tokens & output_tokens):
            satisfied += 1
    return satisfied / len(instructions)


def consistency(i: MetricInput) -> float:
    outputs = _require(i.repeated_outputs, "repeated_outputs")
    if len(outputs) < 2:
        raise MetricComputationError("consistency requires at least 2 repeated_outputs")
    token_sets = [_tokens(o) for o in outputs]
    pairs = [(a, b) for idx, a in enumerate(token_sets) for b in token_sets[idx + 1:]]
    return sum(_jaccard(a, b) for a, b in pairs) / len(pairs)


def formatting_compliance(i: MetricInput) -> float:
    _require(i.actual_output, "actual_output")
    fmt = _require(i.expected_format, "expected_format")
    text = _stringify(i.actual_output)
    if fmt == "json":
        try:
            json.loads(text)
            return 1.0
        except (json.JSONDecodeError, TypeError):
            return 0.0
    if fmt.startswith("regex:"):
        pattern = fmt[len("regex:"):]
        return 1.0 if re.search(pattern, text) else 0.0
    raise MetricComputationError(f"unsupported expected_format '{fmt}' (use 'json' or 'regex:<pattern>')")


def json_validation(i: MetricInput) -> float:
    _require(i.actual_output, "actual_output")
    text = _stringify(i.actual_output)
    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return 0.0
    if i.json_schema_required_keys:
        if not isinstance(parsed, dict):
            return 0.0
        if not all(key in parsed for key in i.json_schema_required_keys):
            return 0.0
    return 1.0


# -- operational metrics ---------------------------------------------------------

def latency(i: MetricInput) -> float:
    value = _require(i.latency_ms, "latency_ms")
    if value < 0:
        raise MetricComputationError("latency_ms cannot be negative")
    return float(value)


def token_usage(i: MetricInput) -> float:
    if i.prompt_tokens is None and i.completion_tokens is None:
        raise MetricComputationError("cannot compute token_usage without prompt_tokens or completion_tokens")
    return float((i.prompt_tokens or 0) + (i.completion_tokens or 0))


def cost(i: MetricInput) -> float:
    value = _require(i.cost, "cost")
    if value < 0:
        raise MetricComputationError("cost cannot be negative")
    return float(value)
