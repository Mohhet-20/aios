"""Trace payloads for Agent and Workflow evaluation. These are the
"what actually happened" record a real Agent/Workflow Platform
observability API would hand back for one execution — planning steps,
tool calls, delegated tasks, node retries, parallel branch timings,
approval latencies. `agent_workflow/analysis.py` turns a trace into
diagnostic scores; `agent_workflow/bridges.py` is how a trace gets
fetched for a given dataset item."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentExecutionTrace:
    success: bool
    final_output: Any = None
    planned_steps: list[str] = field(default_factory=list)
    executed_steps: list[str] = field(default_factory=list)
    delegated_tasks: list[dict] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    memory_retrievals: list[dict] = field(default_factory=list)
    verifications: list[dict] = field(default_factory=list)
    collaborators: list[dict] = field(default_factory=list)
    had_failure: bool = False
    recovered_from_failure: bool = False
    latency_ms: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    cost: float | None = None


@dataclass
class WorkflowExecutionTrace:
    success: bool
    final_output: Any = None
    nodes: list[dict] = field(default_factory=list)
    parallel_branches: list[dict] = field(default_factory=list)
    approvals: list[float] = field(default_factory=list)
    approval_target_latency_ms: float | None = None
    resource_usage: dict = field(default_factory=dict)
    latency_ms: float | None = None
    cost: float | None = None
