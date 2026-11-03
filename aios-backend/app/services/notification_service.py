from __future__ import annotations

from app.domain.events.events import NotificationCreated
from app.events.bus import EventBus
from app.models.notification import NotificationModel
from app.repositories.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self, repository: NotificationRepository, event_bus: EventBus):
        self.repository = repository
        self.event_bus = event_bus

    async def notify(
        self, recipient_user_id: str, title: str, description: str, notification_type: str = "info"
    ) -> NotificationModel:
        notification = NotificationModel(
            recipient_user_id=recipient_user_id,
            title=title,
            description=description,
            notification_type=notification_type,
        )
        notification = await self.repository.add(notification)
        await self.event_bus.publish(
            NotificationCreated(notification_id=notification.id, recipient_user_id=recipient_user_id)
        )
        return notification

    async def list_for_user(self, user_id: str, unread_only: bool = False) -> list[NotificationModel]:
        return await self.repository.list_for_user(user_id, unread_only)

    async def mark_read(self, notification_id: str) -> NotificationModel:
        notification = await self.repository.get_or_404(notification_id)
        notification.read = True
        return await self.repository.update(notification)

    async def mark_all_read(self, user_id: str) -> None:
        for notification in await self.repository.list_for_user(user_id):
            if not notification.read:
                notification.read = True
                await self.repository.update(notification)
