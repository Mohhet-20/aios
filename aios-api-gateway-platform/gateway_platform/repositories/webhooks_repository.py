from __future__ import annotations

from sqlalchemy import select

from gateway_platform.models.webhooks import WebhookDeliveryModel, WebhookSubscriptionModel
from gateway_platform.repositories.base import SQLAlchemyRepository


class WebhookSubscriptionRepository(SQLAlchemyRepository[WebhookSubscriptionModel]):
    model = WebhookSubscriptionModel

    async def list_active(self, tenant_id: str) -> list[WebhookSubscriptionModel]:
        stmt = select(WebhookSubscriptionModel).where(
            WebhookSubscriptionModel.tenant_id == tenant_id, WebhookSubscriptionModel.is_active.is_(True),
            WebhookSubscriptionModel.is_deleted.is_(False),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_tenant(self, tenant_id: str) -> list[WebhookSubscriptionModel]:
        stmt = select(WebhookSubscriptionModel).where(
            WebhookSubscriptionModel.tenant_id == tenant_id, WebhookSubscriptionModel.is_deleted.is_(False)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class WebhookDeliveryRepository(SQLAlchemyRepository[WebhookDeliveryModel]):
    model = WebhookDeliveryModel

    async def list_for_subscription(self, tenant_id: str, subscription_id: str) -> list[WebhookDeliveryModel]:
        stmt = select(WebhookDeliveryModel).where(
            WebhookDeliveryModel.tenant_id == tenant_id, WebhookDeliveryModel.subscription_id == subscription_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_due_for_retry(self, tenant_id: str) -> list[WebhookDeliveryModel]:
        stmt = select(WebhookDeliveryModel).where(
            WebhookDeliveryModel.tenant_id == tenant_id, WebhookDeliveryModel.status == "retrying",
        )
        return list((await self.session.execute(stmt)).scalars().all())
