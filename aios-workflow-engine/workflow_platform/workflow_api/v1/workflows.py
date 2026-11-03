"""Workflow CRUD + lifecycle (publish/pause/resume/deprecate/archive) —
the "Workflow Builder" / "Workflow List" frontend surfaces."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from workflow_platform.core.pagination import PaginationParams
from workflow_platform.workflow_api.dependencies import get_workflow_service
from workflow_platform.workflow_api.serialization import to_dict, to_dict_list
from workflow_platform.workflow_core.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["workflows"])


class CreateWorkflowRequest(BaseModel):
    workspace_id: str
    name: str
    owner_id: str
    category: str
    slug: str | None = None
    description: str | None = None
    tags: list[str] = []
    priority: str = "normal"
    variables: dict = {}
    workflow_metadata: dict = {}


class UpdateWorkflowRequest(BaseModel):
    fields: dict


@router.post("", status_code=201)
async def create_workflow(body: CreateWorkflowRequest, svc: WorkflowService = Depends(get_workflow_service)):
    workflow = await svc.create_workflow(
        body.workspace_id, name=body.name, owner_id=body.owner_id, category=body.category, slug=body.slug,
        description=body.description, tags=body.tags, priority=body.priority, variables=body.variables,
        workflow_metadata=body.workflow_metadata,
    )
    return to_dict(workflow)


@router.get("")
async def list_workflows(
    workspace_id: str, status: str | None = None, category: str | None = None,
    page: int = 1, page_size: int = 20, svc: WorkflowService = Depends(get_workflow_service),
):
    result = await svc.list_workflows(workspace_id, PaginationParams(page=page, page_size=page_size), status=status, category=category)
    return {"items": to_dict_list(result.items), "total": result.total, "page": result.page, "page_size": result.page_size, "total_pages": result.total_pages}


@router.get("/search")
async def search_workflows(workspace_id: str, q: str, svc: WorkflowService = Depends(get_workflow_service)):
    return to_dict_list(await svc.search_workflows(workspace_id, q))


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, svc: WorkflowService = Depends(get_workflow_service)):
    return to_dict(await svc.get_workflow(workflow_id))


@router.patch("/{workflow_id}")
async def update_workflow(workflow_id: str, body: UpdateWorkflowRequest, svc: WorkflowService = Depends(get_workflow_service)):
    return to_dict(await svc.update_workflow(workflow_id, **body.fields))


@router.delete("/{workflow_id}", status_code=204)
async def delete_workflow(workflow_id: str, svc: WorkflowService = Depends(get_workflow_service)):
    await svc.delete_workflow(workflow_id)


@router.post("/{workflow_id}/pause")
async def pause_workflow(workflow_id: str, svc: WorkflowService = Depends(get_workflow_service)):
    return to_dict(await svc.pause(workflow_id))


@router.post("/{workflow_id}/resume")
async def resume_workflow(workflow_id: str, svc: WorkflowService = Depends(get_workflow_service)):
    return to_dict(await svc.resume(workflow_id))


@router.post("/{workflow_id}/deprecate")
async def deprecate_workflow(workflow_id: str, svc: WorkflowService = Depends(get_workflow_service)):
    return to_dict(await svc.deprecate(workflow_id))


@router.post("/{workflow_id}/archive")
async def archive_workflow(workflow_id: str, svc: WorkflowService = Depends(get_workflow_service)):
    return to_dict(await svc.archive(workflow_id))
