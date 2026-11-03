"""Protocol interfaces for fetching a real execution trace from the
Agent Platform / Workflow Engine, plus in-process reference
implementations. This mirrors the Tool Platform's `platform_bridges`
pattern exactly: a `Protocol` the run engines depend on, and a
reference bridge that looks traces up from a dict the caller registers
directly (since this sandbox has no live network path to the actual
Agent/Workflow Platform processes). Swapping the reference bridge for a
real network client to those platforms' observability APIs is a
one-file change — nothing in `executors.py` or the run engines has to
change."""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from eval_platform.agent_workflow.traces import AgentExecutionTrace, WorkflowExecutionTrace
from eval_platform.core.exceptions import EvaluationExecutionError


@runtime_checkable
class AgentPlatformBridge(Protocol):
    async def get_execution_trace(self, ref: dict) -> AgentExecutionTrace: ...


@runtime_checkable
class WorkflowPlatformBridge(Protocol):
    async def get_execution_trace(self, ref: dict) -> WorkflowExecutionTrace: ...


class InMemoryAgentPlatformBridge:
    def __init__(self, traces: dict[str, AgentExecutionTrace] | None = None):
        self._traces = dict(traces or {})

    def register(self, trace_id: str, trace: AgentExecutionTrace) -> None:
        self._traces[trace_id] = trace

    async def get_execution_trace(self, ref: dict) -> AgentExecutionTrace:
        trace_id = ref.get("trace_id")
        if trace_id is None or trace_id not in self._traces:
            raise EvaluationExecutionError(f"no agent execution trace registered for ref {ref!r}")
        return self._traces[trace_id]


class InMemoryWorkflowPlatformBridge:
    def __init__(self, traces: dict[str, WorkflowExecutionTrace] | None = None):
        self._traces = dict(traces or {})

    def register(self, trace_id: str, trace: WorkflowExecutionTrace) -> None:
        self._traces[trace_id] = trace

    async def get_execution_trace(self, ref: dict) -> WorkflowExecutionTrace:
        trace_id = ref.get("trace_id")
        if trace_id is None or trace_id not in self._traces:
            raise EvaluationExecutionError(f"no workflow execution trace registered for ref {ref!r}")
        return self._traces[trace_id]
