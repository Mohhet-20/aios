from fastapi import APIRouter, Depends, Query

from app.dependencies.auth_dependencies import get_current_principal
from app.dependencies.service_dependencies import get_notification_service
from app.schemas.notification import NotificationRead
from app.security.principal import Principal
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=list[NotificationRead])
async def list_notifications(
    unread_only: bool = Query(default=False),
    service: NotificationService = Depends(get_notification_service),
    principal: Principal = Depends(get_current_principal),
):
    return await service.list_for_user(principal.id, unread_only)


@router.post("/{notification_id}/read", response_model=NotificationRead)
async def mark_read(notification_id: str, service: NotificationService = Depends(get_notification_service)):
    return await service.mark_read(notification_id)


@router.post("/read-all", status_code=204)
async def mark_all_read(
    service: NotificationService = Depends(get_notification_service),
    principal: Principal = Depends(get_current_principal),
):
    await service.mark_all_read(principal.id)
