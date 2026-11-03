"""Notifications: create/fan-out, read state, preferences, digest."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from collaboration_platform.collab_api.serialization import to_dict, to_dict_list
from collaboration_platform.dependencies.dependencies import (
    get_digest_service,
    get_notification_preference_service,
    get_notification_service,
)
from collaboration_platform.domain.enums import NotificationType
from collaboration_platform.notifications.digest_service import DigestService
from collaboration_platform.notifications.notification_service import NotificationService
from collaboration_platform.notifications.preference_service import NotificationPreferenceService

router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotifyRequest(BaseModel):
    recipient_id: str
    notification_type: NotificationType
    title: str
    body: str | None = None
    actor_id: str | None = None
    asset_id: str | None = None
    notification_metadata: dict | None = None


@router.post("", status_code=201)
async def notify(body: NotifyRequest, service: NotificationService = Depends(get_notification_service)):
    return to_dict(await service.notify(
        body.recipient_id, body.notification_type, body.title, body=body.body, actor_id=body.actor_id,
        asset_id=body.asset_id, notification_metadata=body.notification_metadata,
    ))


@router.get("/user/{recipient_id}")
async def list_notifications(recipient_id: str, unread_only: bool = False, limit: int = 100, service: NotificationService = Depends(get_notification_service)):
    return to_dict_list(await service.list_for_recipient(recipient_id, unread_only=unread_only, limit=limit))


@router.get("/user/{recipient_id}/unread-count")
async def unread_count(recipient_id: str, service: NotificationService = Depends(get_notification_service)):
    return {"unread_count": await service.count_unread(recipient_id)}


@router.post("/{notification_id}/read")
async def mark_read(notification_id: str, service: NotificationService = Depends(get_notification_service)):
    return to_dict(await service.mark_read(notification_id))


@router.post("/{notification_id}/unread")
async def mark_unread(notification_id: str, service: NotificationService = Depends(get_notification_service)):
    return to_dict(await service.mark_unread(notification_id))


@router.post("/user/{recipient_id}/read-all")
async def mark_all_read(recipient_id: str, service: NotificationService = Depends(get_notification_service)):
    return {"marked_read": await service.mark_all_read(recipient_id)}


class UpdatePreferenceRequest(BaseModel):
    notification_type: str
    in_app_enabled: bool | None = None
    email_enabled: bool | None = None
    digest_enabled: bool | None = None


@router.put("/user/{user_id}/preferences")
async def update_preference(user_id: str, body: UpdatePreferenceRequest, service: NotificationPreferenceService = Depends(get_notification_preference_service)):
    return to_dict(await service.update_preference(
        user_id, body.notification_type, in_app_enabled=body.in_app_enabled, email_enabled=body.email_enabled, digest_enabled=body.digest_enabled,
    ))


@router.get("/user/{user_id}/preferences")
async def list_preferences(user_id: str, service: NotificationPreferenceService = Depends(get_notification_preference_service)):
    return to_dict_list(await service.list_for_user(user_id))


@router.post("/user/{user_id}/digest")
async def build_digest(user_id: str, service: DigestService = Depends(get_digest_service)):
    digest = await service.build_digest(user_id)
    return to_dict(digest) if digest else {"digest": None}
