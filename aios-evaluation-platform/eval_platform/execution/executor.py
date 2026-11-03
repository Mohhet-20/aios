"""TargetExecutor: the single pluggable seam every run engine below
dispatches through to actually produce an output for a dataset item —
whether it's one EvaluationRun scoring a single target, or a
BenchmarkRun comparing several candidates. A `target_config`
(evaluation) and a `candidate` (benchmark) share the same shape:
`{"label"?: str, "type": "prompt"|"agent"|"workflow"|"model"|"tool", ...}`.

`ReferenceTargetExecutor` is a deterministic, config-driven stand-in,
explicitly disclosed as such: it never fabricates a model/agent/
workflow response, it only ever returns what the config already
specifies (a `response_map` keyed by dataset item id, or a
`static_response` fallback), and it measures real wall-clock time
around that lookup. Wiring a target type to a live Prompt/Agent/
Workflow/AI-Core call is a new `TargetExecutor` implementation plugged
in at the call site — mirroring the Tool Platform's `platform_bridges`
Protocol + reference-implementation pattern — never a change to the run
engines that consume it."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from eval_platform.core.exceptions import EvaluationExecutionError


@dataclass
class TargetExecutionResult:
    actual_output: Any
    success: bool = True
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost: float | None = None
    error_message: str | None = None
    # Metrics this executor computed itself that fall outside the standard
    # 20-key metric registry (e.g. agent/workflow diagnostics from
    # `agent_workflow/analysis.py`) — merged into the run engine's
    # per-item `metric_results` alongside the registry-computed ones.
    extra_metrics: dict = field(default_factory=dict)


@runtime_checkable
class TargetExecutor(Protocol):
    async def execute(self, target_config: dict, item: Any) -> TargetExecutionResult: ...


class ReferenceTargetExecutor:
    """Config-driven reference implementation used by default and in
    tests. See module docstring for the disclosed limitation."""

    async def execute(self, target_config: dict, item: Any) -> TargetExecutionResult:
        start = time.perf_counter()
        response_map = target_config.get("response_map") or {}
        if item.id in response_map:
            output = response_map[item.id]
        elif "static_response" in target_config:
            output = target_config["static_response"]
        else:
            label = target_config.get("label", target_config.get("type", "?"))
            raise EvaluationExecutionError(
                f"target '{label}' has no configured response for item '{item.id}' — set 'response_map' or "
                "'static_response' in its config, or supply a live TargetExecutor wired to a real "
                "prompt/agent/workflow/model backend"
            )
        latency_ms = target_config.get("latency_ms_override", (time.perf_counter() - start) * 1000)
        return TargetExecutionResult(
            actual_output=output, success=True, latency_ms=latency_ms,
            prompt_tokens=target_config.get("prompt_tokens"), completion_tokens=target_config.get("completion_tokens"),
            cost=target_config.get("cost"),
        )
