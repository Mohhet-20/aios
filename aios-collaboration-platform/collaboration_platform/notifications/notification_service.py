"""NotificationService: creates a `NotificationModel` and immediately
fans it out to whatever channels the recipient's preferences enable
(via `NotificationDeliveryService`), plus read/unread state and
listing. Notification creation and delivery are deliberately one
call (`notify`) rather than a separate "create" then "dispatch" step
for the in-app/email path — only the digest channel batches and
dispatches later, which is `DigestService`'s job."""
from __future__ import annotations

from collaboration_platform.core.exceptions import NotFoundError
from collaboration_platform.database.base import utcnow
from collaboration_platform.domain.enums import NotificationType
from collaboration_platform.models.notification import NotificationModel
from collaboration_platform.notifications.delivery_service import NotificationDeliveryService, Sender
from collaboration_platform.repositories.registry import RepositoryRegistry


class NotificationService:
    def __init__(self, repos: RepositoryRegistry, *, email_sender: Sender | None = None):
        self.repos = repos
        self.delivery = NotificationDeliveryService(repos, email_sender=email_sender)

    async def notify(
        self, recipient_id: str, notification_type: NotificationType, title: str, *, body: str | None = None,
        actor_id: str | None = None, asset_id: str | None = None, notification_metadata: dict | None = None,
    ) -> NotificationModel:
        notification = await self.repos.notifications.add(NotificationModel(
            recipient_id=recipient_id, notification_type=notification_type.value, title=title, body=body,
            actor_id=actor_id, asset_id=asset_id, notification_metadata=notification_metadata or {},
        ))
        await self.delivery.fan_out(notification)
        return notification

    async def mark_read(self, notification_id: str) -> NotificationModel:
        notification = await self.repos.notifications.get(notification_id)
        if notification is None:
            raise NotFoundError(f"notification '{notification_id}' not found")
        notification.is_read = True
        notification.read_at = utcnow()
        return await self.repos.notifications.update(notification)

    async def mark_unread(self, notification_id: str) -> NotificationModel:
        notification = await self.repos.notifications.get(notification_id)
        if notification is None:
            raise NotFoundError(f"notification '{notification_id}' not found")
        notification.is_read = False
        notification.read_at = None
        return await self.repos.notifications.update(notification)

    async def mark_all_read(self, recipient_id: str) -> int:
        unread = await self.repos.notifications.list_for_recipient(recipient_id, unread_only=True, limit=100000)
        for notification in unread:
            notification.is_read = True
            notification.read_at = utcnow()
            await self.repos.notifications.update(notification)
        return len(unread)

    async def list_for_recipient(self, recipient_id: str, *, unread_only: bool = False, limit: int = 100) -> list[NotificationModel]:
        return await self.repos.notifications.list_for_recipient(recipient_id, unread_only=unread_only, limit=limit)

    async def count_unread(self, recipient_id: str) -> int:
        return await self.repos.notifications.count_unread(recipient_id)
