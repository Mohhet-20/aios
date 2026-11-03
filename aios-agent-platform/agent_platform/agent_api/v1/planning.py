"""Task Planning: goal decomposition, dependency wiring, execution
ordering, resource estimation, progress, and adaptive replanning — the
Task Graph frontend surface reads straight from these endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from agent_platform.agent_api.dependencies import get_planning_service
from agent_platform.agent_api.serialization import to_dict, to_dict_list
from agent_platform.domain.enums import OrchestrationStrategy, TaskPriority
from agent_platform.planner.planning_service import PlanningService

router = APIRouter(prefix="/tasks", tags=["planning"])


class CreateRootTaskRequest(BaseModel):
    workspace_id: str
    title: str
    goal: str
    created_by: str
    priority: TaskPriority = TaskPriority.NORMAL
    orchestration_strategy: OrchestrationStrategy | None = None
    context: dict = {}


class DecomposeRequest(BaseModel):
    max_subtasks: int = 8


class AddDependencyRequest(BaseModel):
    depends_on_task_id: str


class ReplanRequest(BaseModel):
    reason: str
    max_subtasks: int = 8


@router.post("", status_code=201)
async def create_root_task(body: CreateRootTaskRequest, svc: PlanningService = Depends(get_planning_service)):
    task = await svc.create_root_task(
        body.workspace_id, title=body.title, goal=body.goal, created_by=body.created_by,
        priority=body.priority, orchestration_strategy=body.orchestration_strategy, context=body.context,
    )
    return to_dict(task)


@router.post("/{task_id}/decompose", status_code=201)
async def decompose(task_id: str, body: DecomposeRequest, svc: PlanningService = Depends(get_planning_service)):
    return to_dict_list(await svc.decompose(task_id, max_subtasks=body.max_subtasks))


@router.post("/{task_id}/dependencies", status_code=201)
async def add_dependency(task_id: str, body: AddDependencyRequest, svc: PlanningService = Depends(get_planning_service)):
    return to_dict(await svc.add_dependency(task_id, body.depends_on_task_id))


@router.get("/{root_task_id}/execution-order")
async def execution_order(root_task_id: str, svc: PlanningService = Depends(get_planning_service)):
    return {"order": await svc.execution_order(root_task_id)}


@router.get("/{root_task_id}/resource-estimate")
async def estimate_resources(root_task_id: str, svc: PlanningService = Depends(get_planning_service)):
    return await svc.estimate_resources(root_task_id)


@router.get("/{root_task_id}/progress")
async def progress(root_task_id: str, svc: PlanningService = Depends(get_planning_service)):
    return await svc.progress(root_task_id)


@router.post("/{task_id}/replan", status_code=201)
async def replan(task_id: str, body: ReplanRequest, svc: PlanningService = Depends(get_planning_service)):
    return to_dict_list(await svc.replan(task_id, reason=body.reason, max_subtasks=body.max_subtasks))


@router.get("/{task_id}")
async def get_task(task_id: str, svc: PlanningService = Depends(get_planning_service)):
    return to_dict(await svc.repos.tasks.get_or_404(task_id))


@router.get("/root/{root_task_id}/subtasks")
async def list_subtasks(root_task_id: str, svc: PlanningService = Depends(get_planning_service)):
    return to_dict_list(await svc.repos.tasks.list_for_root(root_task_id))
