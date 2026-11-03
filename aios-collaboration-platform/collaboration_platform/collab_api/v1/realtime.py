"""Real-time collaboration: presence/cursors, edit sessions, conflict
detection/resolution, and the CAS/offline-recovery sync guard."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from collaboration_platform.collab_api.serialization import to_dict, to_dict_list
from collaboration_platform.dependencies.dependencies import (
    get_conflict_service,
    get_edit_session_service,
    get_presence_service,
    get_sync_service,
)
from collaboration_platform.domain.enums import ConflictResolutionStrategy
from collaboration_platform.realtime.conflict_service import ConflictService
from collaboration_platform.realtime.edit_session_service import EditSessionService
from collaboration_platform.realtime.presence_service import PresenceService
from collaboration_platform.realtime.sync_service import SyncService

router = APIRouter(prefix="/realtime", tags=["realtime"])


class JoinPresenceRequest(BaseModel):
    user_id: str
    connection_id: str
    cursor_position: dict | None = None


@router.post("/presence/{asset_id}/join", status_code=201)
async def join_presence(asset_id: str, body: JoinPresenceRequest, service: PresenceService = Depends(get_presence_service)):
    return to_dict(await service.join(asset_id, body.user_id, connection_id=body.connection_id, cursor_position=body.cursor_position))


@router.post("/presence/{connection_id}/heartbeat")
async def heartbeat(connection_id: str, service: PresenceService = Depends(get_presence_service)):
    return to_dict(await service.heartbeat(connection_id))


class UpdateCursorRequest(BaseModel):
    cursor_position: dict


@router.put("/presence/{connection_id}/cursor")
async def update_cursor(connection_id: str, body: UpdateCursorRequest, service: PresenceService = Depends(get_presence_service)):
    return to_dict(await service.update_cursor(connection_id, body.cursor_position))


@router.post("/presence/{connection_id}/leave")
async def leave_presence(connection_id: str, service: PresenceService = Depends(get_presence_service)):
    return to_dict(await service.leave(connection_id))


@router.get("/presence/{asset_id}/active")
async def list_active_presence(asset_id: str, service: PresenceService = Depends(get_presence_service)):
    return to_dict_list(await service.list_active(asset_id))


@router.post("/presence/sweep-stale")
async def sweep_stale_presence(service: PresenceService = Depends(get_presence_service)):
    return to_dict_list(await service.sweep_stale())


class StartEditSessionRequest(BaseModel):
    user_id: str
    base_version_id: str | None = None


@router.post("/edit-sessions/{asset_id}/start", status_code=201)
async def start_edit_session(asset_id: str, body: StartEditSessionRequest, service: EditSessionService = Depends(get_edit_session_service)):
    return to_dict(await service.start_session(asset_id, body.user_id, base_version_id=body.base_version_id))


@router.post("/edit-sessions/{session_id}/end")
async def end_edit_session(session_id: str, service: EditSessionService = Depends(get_edit_session_service)):
    return to_dict(await service.end_session(session_id))


@router.get("/edit-sessions/{asset_id}/active")
async def list_active_edit_sessions(asset_id: str, service: EditSessionService = Depends(get_edit_session_service)):
    return to_dict_list(await service.list_active_for_asset(asset_id))


@router.post("/conflicts/{asset_id}/detect")
async def detect_conflicts(asset_id: str, service: ConflictService = Depends(get_conflict_service)):
    return to_dict_list(await service.detect_conflicts(asset_id))


class ResolveConflictRequest(BaseModel):
    strategy: ConflictResolutionStrategy
    resolved_by: str
    notes: str | None = None


@router.post("/conflicts/{conflict_id}/resolve")
async def resolve_conflict(conflict_id: str, body: ResolveConflictRequest, service: ConflictService = Depends(get_conflict_service)):
    return to_dict(await service.resolve(conflict_id, strategy=body.strategy, resolved_by=body.resolved_by, notes=body.notes))


@router.get("/conflicts/unresolved")
async def list_unresolved_conflicts(service: ConflictService = Depends(get_conflict_service)):
    return to_dict_list(await service.list_unresolved())


@router.get("/sync/{asset_id}/check-stale")
async def check_stale(asset_id: str, expected_version_id: str | None = None, service: SyncService = Depends(get_sync_service)):
    await service.assert_not_stale(asset_id, expected_version_id)
    return {"is_stale": False}


@router.get("/sync/edit-sessions/{edit_session_id}/resume")
async def resume_offline_session(edit_session_id: str, service: SyncService = Depends(get_sync_service)):
    return await service.resume_offline_session(edit_session_id)
