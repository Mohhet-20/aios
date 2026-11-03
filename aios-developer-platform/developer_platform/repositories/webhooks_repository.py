from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from developer_platform.models.webhooks import WebhookDeliveryModel, WebhookSubscriptionModel
from developer_platform.repositories.base import SQLAlchemyRepository


class WebhookSubscriptionRepository(SQLAlchemyRepository[WebhookSubscriptionModel]):
    model = WebhookSubscriptionModel

    async def list_active(self, tenant_id: str) -> list[WebhookSubscriptionModel]:
        stmt = select(WebhookSubscriptionModel).where(
            WebhookSubscriptionModel.tenant_id == tenant_id, WebhookSubscriptionModel.is_active.is_(True)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_tenant(self, tenant_id: str) -> list[WebhookSubscriptionModel]:
        stmt = select(WebhookSubscriptionModel).where(WebhookSubscriptionModel.tenant_id == tenant_id)
        return list((await self.session.execute(stmt)).scalars().all())


class WebhookDeliveryRepository(SQLAlchemyRepository[WebhookDeliveryModel]):
    model = WebhookDeliveryModel

    async def list_for_subscription(self, tenant_id: str, subscription_id: str, *, limit: int = 200) -> list[WebhookDeliveryModel]:
        stmt = select(WebhookDeliveryModel).where(
            WebhookDeliveryModel.tenant_id == tenant_id, WebhookDeliveryModel.subscription_id == subscription_id
        ).order_by(WebhookDeliveryModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_due_for_retry(self, tenant_id: str, *, before: datetime) -> list[WebhookDeliveryModel]:
        stmt = select(WebhookDeliveryModel).where(
            WebhookDeliveryModel.tenant_id == tenant_id, WebhookDeliveryModel.status == "failed",
            WebhookDeliveryModel.next_attempt_at.is_not(None), WebhookDeliveryModel.next_attempt_at <= before,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_by_status(self, tenant_id: str, status: str) -> list[WebhookDeliveryModel]:
        stmt = select(WebhookDeliveryModel).where(
            WebhookDeliveryModel.tenant_id == tenant_id, WebhookDeliveryModel.status == status
        )
        return list((await self.session.execute(stmt)).scalars().all())
