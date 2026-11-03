"""Memory CRUD, lifecycle, and search — the primary surface every one of
the 16 memory types is created, retrieved, updated, and retired through.
Conversation/episodic/working memory get their own thin sub-routes since
they have a genuinely different interaction shape (turns, timestamped
events, TTL-bound focus) on top of the same underlying table."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from memory_platform.memory_api.dependencies import (
    get_conversation_memory_service, get_current_actor_id, get_episodic_memory_service, get_memory_service, get_working_memory_service,
)
from memory_platform.memory_api.serialization import to_dict, to_dict_list
from memory_platform.conversation_memory.conversation_memory_service import ConversationMemoryService
from memory_platform.domain.enums import MemoryType
from memory_platform.episodic_memory.episodic_memory_service import EpisodicMemoryService
from memory_platform.memory_core.memory_service import MemoryService
from memory_platform.memory_core.working_memory_service import WorkingMemoryService

router = APIRouter(prefix="/workspaces/{workspace_id}/memory", tags=["memory"])


class CreateMemoryRequest(BaseModel):
    memory_type: MemoryType
    scope_type: str
    scope_id: str
    content: str
    title: str | None = None
    structured_content: dict | None = None
    importance_score: float | None = None
    source: str | None = None
    source_type: str | None = None
    tags: list[str] | None = None
    sensitivity_level: str = "internal"


class UpdateMemoryContentRequest(BaseModel):
    content: str
    structured_content: dict | None = None


class SupersedeMemoryRequest(BaseModel):
    content: str
    structured_content: dict | None = None


class SummarizeMemoryRequest(BaseModel):
    summary_text: str


@router.post("", status_code=201)
async def create_memory(workspace_id: str, body: CreateMemoryRequest, actor_id: str = Depends(get_current_actor_id), svc: MemoryService = Depends(get_memory_service)):
    entry = await svc.create(
        workspace_id=workspace_id, memory_type=body.memory_type, scope_type=body.scope_type, scope_id=body.scope_id, content=body.content,
        actor_id=actor_id, title=body.title, structured_content=body.structured_content, importance_score=body.importance_score,
        source=body.source, source_type=body.source_type, tags=body.tags, sensitivity_level=body.sensitivity_level,
    )
    return to_dict(entry)


@router.get("")
async def list_memory(workspace_id: str, scope_type: str, scope_id: str, memory_type: str | None = None, status: str | None = None, svc: MemoryService = Depends(get_memory_service)):
    return to_dict_list(await svc.list_for_scope(workspace_id, scope_type, scope_id, memory_type=memory_type, status=status))


@router.get("/search")
async def search_memory(workspace_id: str, query: str, memory_type: str | None = None, svc: MemoryService = Depends(get_memory_service)):
    return to_dict_list(await svc.search_keyword(workspace_id, query, memory_type=memory_type))


# -- conversation memory ---------------------------------------------------------------

class AppendTurnRequest(BaseModel):
    conversation_id: str
    scope_type: str
    scope_id: str
    role: str
    content: str


@router.post("/conversations/turns", status_code=201, tags=["conversation-memory"])
async def append_conversation_turn(workspace_id: str, body: AppendTurnRequest, actor_id: str = Depends(get_current_actor_id), svc: ConversationMemoryService = Depends(get_conversation_memory_service)):
    return to_dict(await svc.append_turn(workspace_id=workspace_id, conversation_id=body.conversation_id, scope_type=body.scope_type, scope_id=body.scope_id, role=body.role, content=body.content, actor_id=actor_id))


@router.get("/conversations/{conversation_id}/transcript", tags=["conversation-memory"])
async def get_conversation_transcript(workspace_id: str, conversation_id: str, svc: ConversationMemoryService = Depends(get_conversation_memory_service)):
    return to_dict_list(await svc.get_transcript(conversation_id))


@router.post("/conversations/{conversation_id}/summarize-if-long", tags=["conversation-memory"])
async def summarize_conversation_if_long(workspace_id: str, conversation_id: str, svc: ConversationMemoryService = Depends(get_conversation_memory_service)):
    summary = await svc.summarize_if_long(conversation_id)
    return {"conversation_id": conversation_id, "summary": summary}


# -- episodic memory --------------------------------------------------------------------

class RecordEventRequest(BaseModel):
    scope_type: str
    scope_id: str
    description: str
    occurred_at: datetime | None = None
    structured_content: dict | None = None


@router.post("/episodes", status_code=201, tags=["episodic-memory"])
async def record_episode(workspace_id: str, body: RecordEventRequest, actor_id: str = Depends(get_current_actor_id), svc: EpisodicMemoryService = Depends(get_episodic_memory_service)):
    return to_dict(await svc.record_event(workspace_id=workspace_id, scope_type=body.scope_type, scope_id=body.scope_id, description=body.description, occurred_at=body.occurred_at, structured_content=body.structured_content, actor_id=actor_id))


@router.get("/episodes", tags=["episodic-memory"])
async def query_episodes_by_time_range(workspace_id: str, scope_type: str, scope_id: str, start: datetime, end: datetime, svc: EpisodicMemoryService = Depends(get_episodic_memory_service)):
    return to_dict_list(await svc.query_by_time_range(workspace_id, scope_type, scope_id, start=start, end=end))


# -- working memory ----------------------------------------------------------------------

class SetFocusRequest(BaseModel):
    session_id: str
    content: str
    structured_content: dict | None = None


@router.put("/working-memory/focus", tags=["working-memory"])
async def set_working_memory_focus(workspace_id: str, body: SetFocusRequest, actor_id: str = Depends(get_current_actor_id), svc: WorkingMemoryService = Depends(get_working_memory_service)):
    return to_dict(await svc.set_focus(workspace_id=workspace_id, session_id=body.session_id, content=body.content, structured_content=body.structured_content, actor_id=actor_id))


@router.get("/working-memory/focus", tags=["working-memory"])
async def get_working_memory_focus(workspace_id: str, session_id: str, svc: WorkingMemoryService = Depends(get_working_memory_service)):
    return to_dict(await svc.get_focus(workspace_id, session_id))


@router.delete("/working-memory/focus", status_code=204, tags=["working-memory"])
async def clear_working_memory_focus(workspace_id: str, session_id: str, actor_id: str = Depends(get_current_actor_id), svc: WorkingMemoryService = Depends(get_working_memory_service)):
    await svc.clear_focus(workspace_id, session_id, actor_id=actor_id)


@router.get("/{memory_id}")
async def get_memory(workspace_id: str, memory_id: str, record_access: bool = True, svc: MemoryService = Depends(get_memory_service)):
    return to_dict(await svc.get(memory_id, record_access=record_access))


@router.put("/{memory_id}/content")
async def update_memory_content(workspace_id: str, memory_id: str, body: UpdateMemoryContentRequest, actor_id: str = Depends(get_current_actor_id), svc: MemoryService = Depends(get_memory_service)):
    return to_dict(await svc.update_content(memory_id, body.content, structured_content=body.structured_content, actor_id=actor_id))


@router.post("/{memory_id}/summarize")
async def summarize_memory(workspace_id: str, memory_id: str, body: SummarizeMemoryRequest, actor_id: str = Depends(get_current_actor_id), svc: MemoryService = Depends(get_memory_service)):
    return to_dict(await svc.summarize(memory_id, body.summary_text, actor_id=actor_id))


@router.post("/{memory_id}/summarize-with-llm")
async def summarize_memory_with_llm(workspace_id: str, memory_id: str, actor_id: str = Depends(get_current_actor_id), svc: MemoryService = Depends(get_memory_service)):
    return to_dict(await svc.summarize_with_llm(memory_id, actor_id=actor_id))


@router.post("/{memory_id}/archive")
async def archive_memory(workspace_id: str, memory_id: str, actor_id: str = Depends(get_current_actor_id), svc: MemoryService = Depends(get_memory_service)):
    return to_dict(await svc.archive(memory_id, actor_id=actor_id))


@router.post("/{memory_id}/restore")
async def restore_memory(workspace_id: str, memory_id: str, actor_id: str = Depends(get_current_actor_id), svc: MemoryService = Depends(get_memory_service)):
    return to_dict(await svc.restore(memory_id, actor_id=actor_id))


@router.post("/{memory_id}/expire")
async def expire_memory(workspace_id: str, memory_id: str, actor_id: str = Depends(get_current_actor_id), svc: MemoryService = Depends(get_memory_service)):
    return to_dict(await svc.expire(memory_id, actor_id=actor_id))


@router.post("/{memory_id}/supersede", status_code=201)
async def supersede_memory(workspace_id: str, memory_id: str, body: SupersedeMemoryRequest, actor_id: str = Depends(get_current_actor_id), svc: MemoryService = Depends(get_memory_service)):
    return to_dict(await svc.supersede(memory_id, content=body.content, structured_content=body.structured_content, actor_id=actor_id))

@router.delete("/{memory_id}", status_code=204)
async def delete_memory(workspace_id: str, memory_id: str, hard: bool = False, actor_id: str = Depends(get_current_actor_id), svc: MemoryService = Depends(get_memory_service)):
    await svc.delete(memory_id, actor_id=actor_id, hard=hard)


@router.get("/{memory_id}/decayed-importance")
async def decayed_importance(workspace_id: str, memory_id: str, svc: MemoryService = Depends(get_memory_service)):
    return {"memory_id": memory_id, "decayed_importance": await svc.decayed_importance(memory_id)}


@router.get("/{memory_id}/audit-history")
async def memory_audit_history(workspace_id: str, memory_id: str, svc: MemoryService = Depends(get_memory_service)):
    return to_dict_list(await svc.audit_history(memory_id))


@router.post("/retention/apply")
async def apply_retention(workspace_id: str, actor_id: str = Depends(get_current_actor_id), svc: MemoryService = Depends(get_memory_service)):
    return await svc.apply_retention_policies(workspace_id, actor_id=actor_id)
