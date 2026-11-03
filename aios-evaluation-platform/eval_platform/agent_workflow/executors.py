"""`TargetExecutor` implementations that fetch a real execution trace
via an `AgentPlatformBridge`/`WorkflowPlatformBridge` and turn it into
a `TargetExecutionResult` — `actual_output`/`success`/`latency_ms` feed
the standard metric registry (task_success_rate, latency, ...) exactly
like any other target type, while `extra_metrics` carries the
agent/workflow-specific diagnostics (`agent_planning_quality`,
`workflow_node_reliability`, ...) that a generic actual-vs-expected
comparison can't produce. Both flow through the same
`EvaluationRunService`/`BenchmarkRunService` engines untouched."""
from __future__ import annotations

from eval_platform.agent_workflow.analysis import agent_diagnostics, workflow_diagnostics
from eval_platform.agent_workflow.bridges import AgentPlatformBridge, WorkflowPlatformBridge
from eval_platform.core.exceptions import EvaluationExecutionError
from eval_platform.execution.executor import TargetExecutionResult


def _resolve_ref(target_config: dict, item) -> dict:
    trace_map = target_config.get("trace_map") or {}
    if item.id in trace_map:
        return trace_map[item.id]
    if "ref" in target_config:
        return target_config["ref"]
    raise EvaluationExecutionError(f"target_config has no trace ref for item '{item.id}' — set 'trace_map' or 'ref'")


class AgentTargetExecutor:
    def __init__(self, bridge: AgentPlatformBridge):
        self.bridge = bridge

    async def execute(self, target_config: dict, item) -> TargetExecutionResult:
        ref = _resolve_ref(target_config, item)
        trace = await self.bridge.get_execution_trace(ref)
        return TargetExecutionResult(
            actual_output=trace.final_output, success=trace.success, latency_ms=trace.latency_ms,
            prompt_tokens=trace.prompt_tokens, completion_tokens=trace.completion_tokens, cost=trace.cost,
            extra_metrics=agent_diagnostics(trace),
        )


class WorkflowTargetExecutor:
    def __init__(self, bridge: WorkflowPlatformBridge):
        self.bridge = bridge

    async def execute(self, target_config: dict, item) -> TargetExecutionResult:
        ref = _resolve_ref(target_config, item)
        trace = await self.bridge.get_execution_trace(ref)
        return TargetExecutionResult(
            actual_output=trace.final_output, success=trace.success, latency_ms=trace.latency_ms,
            cost=trace.cost, extra_metrics=workflow_diagnostics(trace),
        )
