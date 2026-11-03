"""Protocol/ABC bridges to the other AIOS platforms this Tool Platform
must integrate with (Workflow Engine, Agent Platform, Prompt Platform,
Memory Platform) — the exact same architectural seam the Workflow
Engine's `ai_bridges/interfaces.py` uses for its own upstream
dependencies. Every one of these is a `Protocol` the engine/planning
code depends on, never a concrete class; `reference_bridges.py` supplies
working in-process implementations so this platform is fully
self-contained and testable without those sibling services actually
running, and swapping a reference bridge for a real network call to a
running Workflow/Agent/Prompt/Memory Platform later is a one-file
change per bridge, not a redesign."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


class WorkflowIntegrationBridge(Protocol):
    async def trigger_workflow(self, workflow_id: str, *, input_variables: dict[str, Any]) -> dict[str, Any]: ...


class AgentIntegrationBridge(Protocol):
    async def notify_agent(self, agent_id: str, *, message: str, context: dict[str, Any]) -> None: ...


class MemoryIntegrationBridge(Protocol):
    async def write_result(self, scope: str, content: dict[str, Any]) -> dict[str, Any]: ...
    async def read_results(self, scope: str) -> list[dict[str, Any]]: ...


class PromptIntegrationBridge(Protocol):
    async def render_prompt(self, prompt_id: str, variables: dict[str, Any]) -> str: ...


@dataclass
class PlatformBridgeSet:
    workflow: WorkflowIntegrationBridge | None = None
    agent: AgentIntegrationBridge | None = None
    memory: MemoryIntegrationBridge | None = None
    prompt: PromptIntegrationBridge | None = None
    extra: dict[str, Any] = field(default_factory=dict)
