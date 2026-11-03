from fastapi import APIRouter, Depends, Query

from app.dependencies.auth_dependencies import require_permission
from app.dependencies.service_dependencies import get_audit_service
from app.schemas.audit import AuditLogRead
from app.security.permissions import Permission
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=list[AuditLogRead])
async def list_audit_logs(
    organization_id: str,
    limit: int = Query(default=100, le=500),
    service: AuditService = Depends(get_audit_service),
    _principal=Depends(require_permission(Permission.AUDIT_READ)),
):
    return await service.list_recent(organization_id, limit)
