"""MetricInput: the single generic payload every metric compute
function reads from. Every field is optional because different metrics
need different signals (a latency metric needs `latency_ms`, a
groundedness metric needs `context_documents`); a metric raises
`MetricComputationError` when the field it needs is missing rather than
fabricating a score, honoring the observability-honesty principle
carried through every other AIOS platform."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricInput:
    actual_output: Any = None
    expected_output: Any = None
    context_documents: list[str] | None = None
    instructions: list[str] | None = None
    reasoning_steps: list[str] | None = None
    expected_reasoning_steps: list[str] | None = None
    plan_steps: list[str] | None = None
    expected_plan_steps: list[str] | None = None
    repeated_outputs: list[str] | None = None
    expected_format: str | None = None
    json_schema_required_keys: list[str] | None = None
    success: bool | None = None
    attempt_count: int | None = None
    retry_count: int | None = None
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost: float | None = None
    extra: dict = field(default_factory=dict)
