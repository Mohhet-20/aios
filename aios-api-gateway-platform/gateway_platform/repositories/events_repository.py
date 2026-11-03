from __future__ import annotations

from sqlalchemy import select

from gateway_platform.models.events import (
    DeadLetterEntryModel,
    EventMessageModel,
    EventSubscriptionModel,
    EventTopicModel,
)
from gateway_platform.repositories.base import SQLAlchemyRepository


class EventTopicRepository(SQLAlchemyRepository[EventTopicModel]):
    model = EventTopicModel

    async def get_by_name(self, tenant_id: str, name: str) -> EventTopicModel | None:
        stmt = select(EventTopicModel).where(
            EventTopicModel.tenant_id == tenant_id, EventTopicModel.name == name, EventTopicModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str) -> list[EventTopicModel]:
        stmt = select(EventTopicModel).where(EventTopicModel.tenant_id == tenant_id, EventTopicModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())


class EventSubscriptionRepository(SQLAlchemyRepository[EventSubscriptionModel]):
    model = EventSubscriptionModel

    async def list_for_topic(self, tenant_id: str, topic_id: str, *, status: str | None = None) -> list[EventSubscriptionModel]:
        stmt = select(EventSubscriptionModel).where(
            EventSubscriptionModel.tenant_id == tenant_id, EventSubscriptionModel.topic_id == topic_id,
            EventSubscriptionModel.is_deleted.is_(False),
        )
        if status:
            stmt = stmt.where(EventSubscriptionModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())


class EventMessageRepository(SQLAlchemyRepository[EventMessageModel]):
    model = EventMessageModel

    async def list_for_topic(self, tenant_id: str, topic_id: str, *, limit: int = 200) -> list[EventMessageModel]:
        stmt = select(EventMessageModel).where(
            EventMessageModel.tenant_id == tenant_id, EventMessageModel.topic_id == topic_id,
        ).order_by(EventMessageModel.published_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_due_for_retry(self, tenant_id: str, *, limit: int = 100) -> list[EventMessageModel]:
        stmt = select(EventMessageModel).where(
            EventMessageModel.tenant_id == tenant_id, EventMessageModel.status == "failed",
        ).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class DeadLetterEntryRepository(SQLAlchemyRepository[DeadLetterEntryModel]):
    model = DeadLetterEntryModel

    async def list_for_topic(self, tenant_id: str, topic_id: str) -> list[DeadLetterEntryModel]:
        stmt = select(DeadLetterEntryModel).where(
            DeadLetterEntryModel.tenant_id == tenant_id, DeadLetterEntryModel.topic_id == topic_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())
