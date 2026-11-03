"""Orchestration: every execution strategy (sequential/parallel/
hierarchical/consensus/supervisor/collaborative), delegation, cancellation,
and checkpoint/recovery — the Execution Timeline / Delegation Graph /
Approval Center frontend surfaces' write side."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from agent_platform.agent_api.dependencies import get_current_actor_id, get_orchestrator
from agent_platform.agent_api.serialization import to_dict
from agent_platform.coordination.orchestrator import TaskOrchestrator
from agent_platform.models.agent import AgentModel

router = APIRouter(prefix="/orchestration", tags=["orchestration"])


async def _resolve_agents(orchestrator: TaskOrchestrator, agent_ids: list[str]) -> list[AgentModel]:
    return [await orchestrator.repos.agents.get_or_404(aid) for aid in agent_ids]


class SequentialRequest(BaseModel):
    agent_ids: list[str]
    stop_on_failure: bool = True


class ParallelRequest(BaseModel):
    agent_ids: list[str]
    max_concurrency: int | None = None


class HierarchicalRequest(BaseModel):
    coordinator_agent_id: str
    worker_agent_ids: list[str]


class ConsensusRequest(BaseModel):
    agent_ids: list[str]
    min_agreement: float = 0.34


class SupervisorRequest(BaseModel):
    supervisor_agent_id: str
    worker_agent_ids: list[str]
    max_rounds: int = 8


class CollaborativeRequest(BaseModel):
    agent_ids: list[str]
    rounds: int = 3


class DelegateRequest(BaseModel):
    from_agent_id: str | None = None
    to_agent_id: str
    reason: str | None = None


class CancelRequest(BaseModel):
    reason: str | None = None


class CheckpointRequest(BaseModel):
    label: str
    state: dict = {}
    agent_id: str | None = None


@router.post("/{root_task_id}/execute-sequential")
async def execute_sequential(
    root_task_id: str, body: SequentialRequest, actor_id: str = Depends(get_current_actor_id),
    orchestrator: TaskOrchestrator = Depends(get_orchestrator),
):
    agents = await _resolve_agents(orchestrator, body.agent_ids)
    return await orchestrator.execute_sequential(root_task_id, agents, stop_on_failure=body.stop_on_failure, triggered_by=actor_id)


@router.post("/{root_task_id}/execute-parallel")
async def execute_parallel(
    root_task_id: str, body: ParallelRequest, actor_id: str = Depends(get_current_actor_id),
    orchestrator: TaskOrchestrator = Depends(get_orchestrator),
):
    agents = await _resolve_agents(orchestrator, body.agent_ids)
    return await orchestrator.execute_parallel(root_task_id, agents, max_concurrency=body.max_concurrency, triggered_by=actor_id)


@router.post("/{root_task_id}/execute-hierarchical")
async def execute_hierarchical(root_task_id: str, body: HierarchicalRequest, orchestrator: TaskOrchestrator = Depends(get_orchestrator)):
    coordinator = await orchestrator.repos.agents.get_or_404(body.coordinator_agent_id)
    workers = await _resolve_agents(orchestrator, body.worker_agent_ids)
    return await orchestrator.execute_hierarchical(root_task_id, coordinator, workers)


@router.post("/{task_id}/execute-consensus")
async def execute_consensus(task_id: str, body: ConsensusRequest, orchestrator: TaskOrchestrator = Depends(get_orchestrator)):
    agents = await _resolve_agents(orchestrator, body.agent_ids)
    return await orchestrator.execute_consensus(task_id, agents, min_agreement=body.min_agreement)


@router.post("/{root_task_id}/execute-supervisor")
async def execute_supervisor(root_task_id: str, body: SupervisorRequest, orchestrator: TaskOrchestrator = Depends(get_orchestrator)):
    supervisor = await orchestrator.repos.agents.get_or_404(body.supervisor_agent_id)
    workers = await _resolve_agents(orchestrator, body.worker_agent_ids)
    return await orchestrator.execute_supervisor(root_task_id, supervisor, workers, max_rounds=body.max_rounds)


@router.post("/{root_task_id}/execute-collaborative")
async def execute_collaborative(root_task_id: str, body: CollaborativeRequest, orchestrator: TaskOrchestrator = Depends(get_orchestrator)):
    agents = await _resolve_agents(orchestrator, body.agent_ids)
    return await orchestrator.execute_collaborative(root_task_id, agents, rounds=body.rounds)


@router.post("/{task_id}/delegate", status_code=201)
async def delegate(task_id: str, body: DelegateRequest, orchestrator: TaskOrchestrator = Depends(get_orchestrator)):
    delegation = await orchestrator.delegate(task_id, body.from_agent_id, body.to_agent_id, reason=body.reason)
    return to_dict(delegation)


@router.post("/{root_task_id}/cancel", status_code=204)
async def cancel(root_task_id: str, body: CancelRequest, orchestrator: TaskOrchestrator = Depends(get_orchestrator)):
    await orchestrator.cancel(root_task_id, reason=body.reason)


@router.post("/{task_id}/checkpoint", status_code=201)
async def checkpoint(task_id: str, body: CheckpointRequest, orchestrator: TaskOrchestrator = Depends(get_orchestrator)):
    return to_dict(await orchestrator.checkpoint(task_id, body.label, body.state, agent_id=body.agent_id))


@router.post("/{task_id}/recover")
async def recover(task_id: str, orchestrator: TaskOrchestrator = Depends(get_orchestrator)):
    return await orchestrator.recover(task_id)
