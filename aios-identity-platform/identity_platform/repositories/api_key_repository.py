from __future__ import annotations

from sqlalchemy import select

from identity_platform.models.api_key import ApiKeyModel, ServiceAccountModel, WebhookSecretModel
from identity_platform.repositories.base import SQLAlchemyRepository


class ApiKeyRepository(SQLAlchemyRepository[ApiKeyModel]):
    model = ApiKeyModel

    async def get_by_key_hash(self, key_hash: str) -> ApiKeyModel | None:
        stmt = select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_owner(self, owner_type: str, owner_id: str) -> list[ApiKeyModel]:
        stmt = select(ApiKeyModel).where(ApiKeyModel.owner_type == owner_type, ApiKeyModel.owner_id == owner_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_organization(self, organization_id: str) -> list[ApiKeyModel]:
        stmt = select(ApiKeyModel).where(ApiKeyModel.organization_id == organization_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_expired_active(self, *, older_than) -> list[ApiKeyModel]:
        stmt = select(ApiKeyModel).where(ApiKeyModel.status == "active", ApiKeyModel.expires_at.is_not(None), ApiKeyModel.expires_at <= older_than)
        return list((await self.session.execute(stmt)).scalars().all())


class ServiceAccountRepository(SQLAlchemyRepository[ServiceAccountModel]):
    model = ServiceAccountModel

    async def list_for_organization(self, organization_id: str) -> list[ServiceAccountModel]:
        stmt = select(ServiceAccountModel).where(ServiceAccountModel.organization_id == organization_id)
        return list((await self.session.execute(stmt)).scalars().all())


class WebhookSecretRepository(SQLAlchemyRepository[WebhookSecretModel]):
    model = WebhookSecretModel

    async def list_for_organization(self, organization_id: str) -> list[WebhookSecretModel]:
        stmt = select(WebhookSecretModel).where(WebhookSecretModel.organization_id == organization_id)
        return list((await self.session.execute(stmt)).scalars().all())
