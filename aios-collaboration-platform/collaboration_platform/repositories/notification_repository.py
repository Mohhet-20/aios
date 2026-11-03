from __future__ import annotations

from sqlalchemy import desc, select

from collaboration_platform.models.notification import (
    NotificationDeliveryModel,
    NotificationModel,
    NotificationPreferenceModel,
)
from collaboration_platform.repositories.base import SQLAlchemyRepository


class NotificationRepository(SQLAlchemyRepository[NotificationModel]):
    model = NotificationModel

    async def list_for_recipient(self, recipient_id: str, *, unread_only: bool = False, limit: int = 100) -> list[NotificationModel]:
        stmt = select(NotificationModel).where(NotificationModel.recipient_id == recipient_id)
        if unread_only:
            stmt = stmt.where(NotificationModel.is_read.is_(False))
        stmt = stmt.order_by(desc(NotificationModel.created_at)).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_unread(self, recipient_id: str) -> int:
        return len(await self.list_for_recipient(recipient_id, unread_only=True, limit=100000))


class NotificationPreferenceRepository(SQLAlchemyRepository[NotificationPreferenceModel]):
    model = NotificationPreferenceModel

    async def get_for_user_and_type(self, user_id: str, notification_type: str) -> NotificationPreferenceModel | None:
        stmt = select(NotificationPreferenceModel).where(
            NotificationPreferenceModel.user_id == user_id,
            NotificationPreferenceModel.notification_type == notification_type,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_user(self, user_id: str) -> list[NotificationPreferenceModel]:
        stmt = select(NotificationPreferenceModel).where(NotificationPreferenceModel.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())


class NotificationDeliveryRepository(SQLAlchemyRepository[NotificationDeliveryModel]):
    model = NotificationDeliveryModel

    async def list_for_notification(self, notification_id: str) -> list[NotificationDeliveryModel]:
        stmt = select(NotificationDeliveryModel).where(NotificationDeliveryModel.notification_id == notification_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_by_status(self, status: str, *, limit: int = 200) -> list[NotificationDeliveryModel]:
        stmt = select(NotificationDeliveryModel).where(NotificationDeliveryModel.status == status).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
