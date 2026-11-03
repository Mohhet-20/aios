"""Inter-Agent Communication: direct/broadcast/status/handoff/event/log
messages plus the per-task shared workspace (blackboard) — the
Conversation Inspector frontend surface's data source."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from agent_platform.agent_api.dependencies import get_communication_service
from agent_platform.agent_api.serialization import to_dict, to_dict_list
from agent_platform.communication.communication_service import CommunicationService

router = APIRouter(prefix="/communication", tags=["communication"])


class SendDirectRequest(BaseModel):
    task_id: str | None = None
    from_agent_id: str
    to_agent_id: str
    content: str
    structured_payload: dict | None = None


class BroadcastRequest(BaseModel):
    task_id: str | None = None
    from_agent_id: str | None = None
    content: str
    structured_payload: dict | None = None


class SharedValueRequest(BaseModel):
    key: str
    value: dict
    updated_by: str | None = None


@router.post("/messages/direct", status_code=201)
async def send_direct(body: SendDirectRequest, svc: CommunicationService = Depends(get_communication_service)):
    return to_dict(await svc.send_direct(body.task_id, body.from_agent_id, body.to_agent_id, body.content, structured_payload=body.structured_payload))


@router.post("/messages/broadcast", status_code=201)
async def broadcast(body: BroadcastRequest, svc: CommunicationService = Depends(get_communication_service)):
    return to_dict(await svc.broadcast(body.task_id, body.from_agent_id, body.content, structured_payload=body.structured_payload))


@router.get("/tasks/{task_id}/conversation")
async def get_conversation(task_id: str, svc: CommunicationService = Depends(get_communication_service)):
    return to_dict_list(await svc.get_conversation(task_id))


@router.get("/agents/{agent_id}/messages")
async def get_agent_messages(agent_id: str, svc: CommunicationService = Depends(get_communication_service)):
    return to_dict_list(await svc.get_agent_messages(agent_id))


@router.put("/tasks/{task_id}/shared-workspace")
async def set_shared_value(task_id: str, body: SharedValueRequest, svc: CommunicationService = Depends(get_communication_service)):
    return to_dict(await svc.set_shared_value(task_id, body.key, body.value, updated_by=body.updated_by))


@router.get("/tasks/{task_id}/shared-workspace/{key}")
async def get_shared_value(task_id: str, key: str, svc: CommunicationService = Depends(get_communication_service)):
    return {"key": key, "value": await svc.get_shared_value(task_id, key)}


@router.get("/tasks/{task_id}/shared-workspace")
async def list_shared_workspace(task_id: str, svc: CommunicationService = Depends(get_communication_service)):
    return to_dict_list(await svc.list_shared_workspace(task_id))
