from fastapi import APIRouter, Depends

from app.dependencies.auth_dependencies import require_permission
from app.dependencies.service_dependencies import get_memory_service
from app.schemas.memory import MemoryItemRead, MemoryQueryRequest, MemoryWriteRequest
from app.security.permissions import Permission
from app.services.memory_service import MemoryService

router = APIRouter(prefix="/memory", tags=["Memory"])


@router.post("", response_model=MemoryItemRead)
async def write_memory(
    payload: MemoryWriteRequest,
    service: MemoryService = Depends(get_memory_service),
    _principal=Depends(require_permission(Permission.MEMORY_WRITE)),
):
    return await service.write(payload.workspace_id, payload.memory_type, payload.scope, payload.content)


@router.post("/query", response_model=list[MemoryItemRead])
async def query_memory(
    payload: MemoryQueryRequest,
    service: MemoryService = Depends(get_memory_service),
    _principal=Depends(require_permission(Permission.MEMORY_READ)),
):
    return await service.query(payload.workspace_id, payload.query, payload.memory_type, payload.top_k)
