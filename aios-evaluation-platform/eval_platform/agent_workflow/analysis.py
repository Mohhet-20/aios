"""Agent and Workflow diagnostic scoring. These sit alongside — but
outside — the fixed 20-key `MetricCategory` registry in `metrics/`,
because they measure things a generic actual-vs-expected-output
comparison can't: whether an agent delegated well, chose the right
tool, used memory relevantly, recovered from failure, or whether a
workflow's nodes were reliable, its parallel branches were efficient,
and its approval steps were timely. Every function reads only from a
trace and raises `EvaluationExecutionError` when the trace doesn't
carry the signal it needs, rather than fabricating a score — the same
honesty principle as every metric in `metrics/functions.py`.
`agent_diagnostics`/`workflow_diagnostics` compute whichever of these
apply to a given trace and silently skip (never fake) the rest."""
from __future__ import annotations

from eval_platform.agent_workflow.traces import AgentExecutionTrace, WorkflowExecutionTrace
from eval_platform.core.exceptions import EvaluationExecutionError

_DEFAULT_APPROVAL_TARGET_MS = 3_600_000.0  # 1 hour


def _require_nonempty(items, field_name: str, metric_name: str):
    if not items:
        raise EvaluationExecutionError(f"{metric_name} requires '{field_name}' on the trace")
    return items


# -- agent diagnostics ---------------------------------------------------------

def agent_task_completion(trace: AgentExecutionTrace) -> float:
    return 1.0 if trace.success else 0.0


def agent_planning_quality(trace: AgentExecutionTrace) -> float:
    _require_nonempty(trace.planned_steps, "planned_steps", "agent_planning_quality")
    _require_nonempty(trace.executed_steps, "executed_steps", "agent_planning_quality")
    planned, executed = set(trace.planned_steps), set(trace.executed_steps)
    return len(planned & executed) / len(planned | executed)


def agent_delegation_quality(trace: AgentExecutionTrace) -> float:
    tasks = _require_nonempty(trace.delegated_tasks, "delegated_tasks", "agent_delegation_quality")
    return sum(1 for t in tasks if t.get("completed")) / len(tasks)


def agent_tool_selection_quality(trace: AgentExecutionTrace) -> float:
    calls = _require_nonempty(trace.tool_calls, "tool_calls", "agent_tool_selection_quality")
    return sum(1 for c in calls if c.get("selected_correctly")) / len(calls)


def agent_memory_usage_quality(trace: AgentExecutionTrace) -> float:
    retrievals = _require_nonempty(trace.memory_retrievals, "memory_retrievals", "agent_memory_usage_quality")
    return sum(1 for m in retrievals if m.get("relevant")) / len(retrievals)


def agent_recovery_quality(trace: AgentExecutionTrace) -> float:
    if not trace.had_failure:
        raise EvaluationExecutionError("agent_recovery_quality only applies when the trace records had_failure=True")
    return 1.0 if trace.recovered_from_failure else 0.0


def agent_verification_quality(trace: AgentExecutionTrace) -> float:
    verifications = _require_nonempty(trace.verifications, "verifications", "agent_verification_quality")
    return sum(1 for v in verifications if v.get("passed")) / len(verifications)


def agent_collaboration_quality(trace: AgentExecutionTrace) -> float:
    collaborators = _require_nonempty(trace.collaborators, "collaborators", "agent_collaboration_quality")
    return sum(1 for c in collaborators if c.get("successful")) / len(collaborators)


_AGENT_DIAGNOSTICS = [
    ("agent_task_completion", agent_task_completion),
    ("agent_planning_quality", agent_planning_quality),
    ("agent_delegation_quality", agent_delegation_quality),
    ("agent_tool_selection_quality", agent_tool_selection_quality),
    ("agent_memory_usage_quality", agent_memory_usage_quality),
    ("agent_recovery_quality", agent_recovery_quality),
    ("agent_verification_quality", agent_verification_quality),
    ("agent_collaboration_quality", agent_collaboration_quality),
]


def agent_diagnostics(trace: AgentExecutionTrace) -> dict[str, float]:
    results = {}
    for key, fn in _AGENT_DIAGNOSTICS:
        try:
            results[key] = fn(trace)
        except EvaluationExecutionError:
            continue
    return results


# -- workflow diagnostics -------------------------------------------------------

def workflow_execution_success(trace: WorkflowExecutionTrace) -> float:
    return 1.0 if trace.success else 0.0


def workflow_node_reliability(trace: WorkflowExecutionTrace) -> float:
    nodes = _require_nonempty(trace.nodes, "nodes", "workflow_node_reliability")
    return sum(1 for n in nodes if n.get("status") == "succeeded") / len(nodes)


def workflow_recovery_quality(trace: WorkflowExecutionTrace) -> float:
    retried = [n for n in trace.nodes if n.get("retries", 0) > 0]
    if not retried:
        raise EvaluationExecutionError("workflow_recovery_quality only applies when at least one node retried")
    return sum(1 for n in retried if n.get("status") == "succeeded") / len(retried)


def workflow_parallel_execution_efficiency(trace: WorkflowExecutionTrace) -> float:
    branches = _require_nonempty(trace.parallel_branches, "parallel_branches", "workflow_parallel_execution_efficiency")
    durations = [b.get("duration_ms") for b in branches if b.get("duration_ms") is not None]
    if not durations:
        raise EvaluationExecutionError("workflow_parallel_execution_efficiency requires branch 'duration_ms' values")
    actual_parallel = max(durations)
    if actual_parallel <= 0:
        return 1.0
    ideal_parallel = sum(durations) / len(durations)
    return min(1.0, ideal_parallel / actual_parallel)


def workflow_approval_flow_efficiency(trace: WorkflowExecutionTrace) -> float:
    approvals = _require_nonempty(trace.approvals, "approvals", "workflow_approval_flow_efficiency")
    avg_latency = sum(approvals) / len(approvals)
    if avg_latency <= 0:
        return 1.0
    target = trace.approval_target_latency_ms or _DEFAULT_APPROVAL_TARGET_MS
    return min(1.0, target / avg_latency)


def workflow_resource_usage_score(trace: WorkflowExecutionTrace) -> float:
    cpu = trace.resource_usage.get("cpu_seconds")
    budget = trace.resource_usage.get("budget_cpu_seconds")
    if cpu is None or budget is None:
        raise EvaluationExecutionError("workflow_resource_usage_score requires resource_usage.cpu_seconds and .budget_cpu_seconds")
    if cpu <= 0:
        return 1.0
    return min(1.0, budget / cpu)


_WORKFLOW_DIAGNOSTICS = [
    ("workflow_execution_success", workflow_execution_success),
    ("workflow_node_reliability", workflow_node_reliability),
    ("workflow_recovery_quality", workflow_recovery_quality),
    ("workflow_parallel_execution_efficiency", workflow_parallel_execution_efficiency),
    ("workflow_approval_flow_efficiency", workflow_approval_flow_efficiency),
    ("workflow_resource_usage_score", workflow_resource_usage_score),
]


def workflow_diagnostics(trace: WorkflowExecutionTrace) -> dict[str, float]:
    results = {}
    for key, fn in _WORKFLOW_DIAGNOSTICS:
        try:
            results[key] = fn(trace)
        except EvaluationExecutionError:
            continue
    return results
