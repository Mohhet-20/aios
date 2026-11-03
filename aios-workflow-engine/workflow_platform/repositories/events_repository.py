from __future__ import annotations

from sqlalchemy import select

from workflow_platform.models.events import EventModel, SubscriptionModel, WebhookDeliveryModel
from workflow_platform.repositories.base import SQLAlchemyRepository


class EventRepository(SQLAlchemyRepository[EventModel]):
    model = EventModel

    async def list_for_workspace(self, workspace_id: str, *, event_type: str | None = None, limit: int = 200) -> list[EventModel]:
        stmt = select(EventModel).where(EventModel.workspace_id == workspace_id)
        if event_type:
            stmt = stmt.where(EventModel.event_type == event_type)
        stmt = stmt.order_by(EventModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_source(self, source_type: str, source_id: str) -> list[EventModel]:
        stmt = select(EventModel).where(
            EventModel.source_type == source_type, EventModel.source_id == source_id
        ).order_by(EventModel.created_at)
        return list((await self.session.execute(stmt)).scalars().all())


class SubscriptionRepository(SQLAlchemyRepository[SubscriptionModel]):
    model = SubscriptionModel

    async def list_for_event_type(self, workspace_id: str, event_type: str) -> list[SubscriptionModel]:
        stmt = select(SubscriptionModel).where(
            SubscriptionModel.workspace_id == workspace_id,
            SubscriptionModel.event_type == event_type,
            SubscriptionModel.is_active.is_(True),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_workspace(self, workspace_id: str) -> list[SubscriptionModel]:
        stmt = select(SubscriptionModel).where(SubscriptionModel.workspace_id == workspace_id)
        return list((await self.session.execute(stmt)).scalars().all())


class WebhookDeliveryRepository(SQLAlchemyRepository[WebhookDeliveryModel]):
    model = WebhookDeliveryModel

    async def list_for_subscription(self, subscription_id: str) -> list[WebhookDeliveryModel]:
        stmt = select(WebhookDeliveryModel).where(WebhookDeliveryModel.subscription_id == subscription_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_pending_retries(self, *, max_attempts: int = 5, limit: int = 100) -> list[WebhookDeliveryModel]:
        """Deliveries not yet DELIVERED and still under the attempt cap —
        `WebhookDeliveryStatus` has no separate "retrying" state (a failed
        delivery just stays FAILED until a retry sweep either delivers it
        or it's abandoned), so this is what a scheduler-driven retry sweep
        (see Task 89) polls."""
        stmt = select(WebhookDeliveryModel).where(
            WebhookDeliveryModel.status.in_(["pending", "failed"]),
            WebhookDeliveryModel.attempt_count < max_attempts,
        ).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
