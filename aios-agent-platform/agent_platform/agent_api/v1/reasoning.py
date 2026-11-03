"""Reasoning & Reflection: chain-of-thought/tree-of-thought traces plus
critique/self-correction cycles — the Reasoning Viewer frontend
surface."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from agent_platform.agent_api.dependencies import get_reasoning_service, get_reflection_service
from agent_platform.agent_api.serialization import to_dict, to_dict_list
from agent_platform.domain.enums import ReasoningMode
from agent_platform.reasoning.reasoning_service import ReasoningService
from agent_platform.reflection.reflection_service import ReflectionService

router = APIRouter(tags=["reasoning"])


class ThinkRequest(BaseModel):
    agent_id: str
    task_id: str
    mode: ReasoningMode = ReasoningMode.CHAIN_OF_THOUGHT
    execution_id: str | None = None
    branches: int = 3
    max_steps: int = 5
    extra_context: str | None = None


class CritiqueRequest(BaseModel):
    response_content: str
    task_id: str
    reflecting_agent_id: str
    execution_id: str
    iteration: int = 1


@router.post("/reasoning/think", status_code=201)
async def think(body: ThinkRequest, reasoning: ReasoningService = Depends(get_reasoning_service)):
    agent = await reasoning.repos.agents.get_or_404(body.agent_id)
    task = await reasoning.repos.tasks.get_or_404(body.task_id)
    trace = await reasoning.think(
        agent, task, mode=body.mode, execution_id=body.execution_id, branches=body.branches,
        max_steps=body.max_steps, extra_context=body.extra_context,
    )
    return to_dict(trace)


@router.get("/tasks/{task_id}/reasoning-traces")
async def list_reasoning_traces(task_id: str, reasoning: ReasoningService = Depends(get_reasoning_service)):
    return to_dict_list(await reasoning.list_for_task(task_id))


@router.post("/reflection/critique", status_code=201)
async def critique(body: CritiqueRequest, reflection: ReflectionService = Depends(get_reflection_service)):
    task = await reflection.repos.tasks.get_or_404(body.task_id)
    reflecting_agent = await reflection.repos.agents.get_or_404(body.reflecting_agent_id)
    result = await reflection.critique(
        response_content=body.response_content, task=task, reflecting_agent=reflecting_agent,
        execution_id=body.execution_id, iteration=body.iteration,
    )
    return to_dict(result)


@router.get("/tasks/{task_id}/reflections")
async def list_reflections(task_id: str, reflection: ReflectionService = Depends(get_reflection_service)):
    return to_dict_list(await reflection.list_for_task(task_id))
