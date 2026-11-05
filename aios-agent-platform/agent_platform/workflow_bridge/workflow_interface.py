"""Workflow Integration: a clean interface for pause/resume/retry/
checkpointing that a future, standalone Workflow Engine plugs into. Per
the agent platform scope boundary ("Do NOT build the Workflow Engine"), this
platform defines the contract and ships one reference implementation that
makes the boundary explicit — calling any of these methods today raises
`WorkflowEngineNotIntegratedError`, not because the capability is
impossible, but because it deliberately belongs to a later project.

This is a different thing from TaskOrchestrator's own `cancel` /
`checkpoint` / `recover` (in `coordination/orchestrator.py`), which ARE
real and already implemented — those are task-execution-scoped
interruptibility and failure recovery, explicitly in-scope for
ORCHESTRATION. This interface is reserved for a general-purpose durable
workflow engine (multi-step business processes spanning many task trees,
human-in-the-loop waits measured in days, cross-system sagas) that sits
above the orchestration layer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class WorkflowEngineNotIntegratedError(NotImplementedError):
    """Raised by the reference WorkflowEngine implementation — the seam is
    wired, the engine behind it is future scope."""


class WorkflowEngine(ABC):
    @abstractmethod
    async def start(self, workflow_key: str, *, context: dict) -> str: ...

    @abstractmethod
    async def pause(self, workflow_execution_id: str) -> None: ...

    @abstractmethod
    async def resume(self, workflow_execution_id: str) -> None: ...

    @abstractmethod
    async def retry(self, workflow_execution_id: str) -> None: ...

    @abstractmethod
    async def checkpoint(self, workflow_execution_id: str, state: dict) -> None: ...


class NotIntegratedWorkflowEngine(WorkflowEngine):
    """The default binding: every method raises with a clear pointer to
    what's real today (TaskOrchestrator) versus what this seam is for."""

    _MESSAGE = (
        "No Workflow Engine is integrated in this platform (out of scope for this platform). "
        "For task-execution-scoped interruption and recovery, use TaskOrchestrator.cancel/checkpoint/recover instead."
    )

    async def start(self, workflow_key: str, *, context: dict) -> str:
        raise WorkflowEngineNotIntegratedError(self._MESSAGE)

    async def pause(self, workflow_execution_id: str) -> None:
        raise WorkflowEngineNotIntegratedError(self._MESSAGE)

    async def resume(self, workflow_execution_id: str) -> None:
        raise WorkflowEngineNotIntegratedError(self._MESSAGE)

    async def retry(self, workflow_execution_id: str) -> None:
        raise WorkflowEngineNotIntegratedError(self._MESSAGE)

    async def checkpoint(self, workflow_execution_id: str, state: dict) -> None:
        raise WorkflowEngineNotIntegratedError(self._MESSAGE)
