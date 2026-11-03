"""Task assignments, checklists, bookmarks, and pinned items."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from collaboration_platform.collab_api.serialization import to_dict, to_dict_list
from collaboration_platform.dependencies.dependencies import (
    get_bookmark_service,
    get_checklist_service,
    get_pinned_service,
    get_task_service,
)
from collaboration_platform.productivity.bookmark_service import BookmarkService
from collaboration_platform.productivity.checklist_service import ChecklistService
from collaboration_platform.productivity.pinned_service import PinnedItemService
from collaboration_platform.productivity.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["productivity"])


class CreateTaskRequest(BaseModel):
    workspace_id: str
    title: str
    created_by: str
    project_id: str | None = None
    asset_id: str | None = None
    assignee_id: str | None = None
    description: str | None = None
    due_date: datetime | None = None


@router.post("", status_code=201)
async def create_task(body: CreateTaskRequest, service: TaskService = Depends(get_task_service)):
    return to_dict(await service.create_task(
        body.workspace_id, title=body.title, created_by=body.created_by, project_id=body.project_id, asset_id=body.asset_id,
        assignee_id=body.assignee_id, description=body.description, due_date=body.due_date,
    ))


@router.get("/workspace/{workspace_id}")
async def list_tasks(workspace_id: str, status: str | None = None, service: TaskService = Depends(get_task_service)):
    return to_dict_list(await service.list_for_workspace(workspace_id, status=status))


@router.get("/assignee/{assignee_id}")
async def list_for_assignee(assignee_id: str, status: str | None = None, service: TaskService = Depends(get_task_service)):
    return to_dict_list(await service.list_for_assignee(assignee_id, status=status))


class AssignTaskRequest(BaseModel):
    assignee_id: str | None = None


@router.put("/{task_id}/assign")
async def assign_task(task_id: str, body: AssignTaskRequest, service: TaskService = Depends(get_task_service)):
    return to_dict(await service.assign(task_id, body.assignee_id))


@router.post("/{task_id}/start")
async def start_task(task_id: str, service: TaskService = Depends(get_task_service)):
    return to_dict(await service.start(task_id))


@router.post("/{task_id}/complete")
async def complete_task(task_id: str, service: TaskService = Depends(get_task_service)):
    return to_dict(await service.complete(task_id))


@router.post("/{task_id}/reopen")
async def reopen_task(task_id: str, service: TaskService = Depends(get_task_service)):
    return to_dict(await service.reopen(task_id))


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: str, service: TaskService = Depends(get_task_service)):
    return to_dict(await service.cancel(task_id))


checklists_router = APIRouter(prefix="/checklists", tags=["productivity"])


class CreateChecklistRequest(BaseModel):
    title: str
    created_by: str
    task_id: str | None = None
    asset_id: str | None = None


@checklists_router.post("", status_code=201)
async def create_checklist(body: CreateChecklistRequest, service: ChecklistService = Depends(get_checklist_service)):
    return to_dict(await service.create_checklist(title=body.title, created_by=body.created_by, task_id=body.task_id, asset_id=body.asset_id))


class AddChecklistItemRequest(BaseModel):
    text: str
    position: int | None = None


@checklists_router.post("/{checklist_id}/items", status_code=201)
async def add_checklist_item(checklist_id: str, body: AddChecklistItemRequest, service: ChecklistService = Depends(get_checklist_service)):
    return to_dict(await service.add_item(checklist_id, text=body.text, position=body.position))


@checklists_router.post("/items/{item_id}/toggle")
async def toggle_checklist_item(item_id: str, service: ChecklistService = Depends(get_checklist_service)):
    return to_dict(await service.toggle_item(item_id))


@checklists_router.get("/{checklist_id}/items")
async def list_checklist_items(checklist_id: str, service: ChecklistService = Depends(get_checklist_service)):
    return to_dict_list(await service.list_items(checklist_id))


bookmarks_router = APIRouter(prefix="/bookmarks", tags=["productivity"])


class AddBookmarkRequest(BaseModel):
    note: str | None = None


@bookmarks_router.post("/{user_id}/{asset_id}", status_code=201)
async def add_bookmark(user_id: str, asset_id: str, body: AddBookmarkRequest, service: BookmarkService = Depends(get_bookmark_service)):
    return to_dict(await service.add_bookmark(user_id, asset_id, note=body.note))


@bookmarks_router.delete("/{user_id}/{asset_id}", status_code=204)
async def remove_bookmark(user_id: str, asset_id: str, service: BookmarkService = Depends(get_bookmark_service)):
    await service.remove_bookmark(user_id, asset_id)


@bookmarks_router.get("/{user_id}")
async def list_bookmarks(user_id: str, service: BookmarkService = Depends(get_bookmark_service)):
    return to_dict_list(await service.list_for_user(user_id))


pinned_router = APIRouter(prefix="/pinned", tags=["productivity"])


@pinned_router.post("/{user_id}/{workspace_id}/{asset_id}", status_code=201)
async def pin_item(user_id: str, workspace_id: str, asset_id: str, service: PinnedItemService = Depends(get_pinned_service)):
    return to_dict(await service.pin(user_id, workspace_id, asset_id))


@pinned_router.delete("/{pinned_item_id}", status_code=204)
async def unpin_item(pinned_item_id: str, service: PinnedItemService = Depends(get_pinned_service)):
    await service.unpin(pinned_item_id)


@pinned_router.get("/{user_id}/{workspace_id}")
async def list_pinned(user_id: str, workspace_id: str, service: PinnedItemService = Depends(get_pinned_service)):
    return to_dict_list(await service.list_for_user_and_workspace(user_id, workspace_id))


class ReorderPinnedRequest(BaseModel):
    ordered_asset_ids: list[str]


@pinned_router.put("/{user_id}/{workspace_id}/reorder")
async def reorder_pinned(user_id: str, workspace_id: str, body: ReorderPinnedRequest, service: PinnedItemService = Depends(get_pinned_service)):
    return to_dict_list(await service.reorder(user_id, workspace_id, body.ordered_asset_ids))
