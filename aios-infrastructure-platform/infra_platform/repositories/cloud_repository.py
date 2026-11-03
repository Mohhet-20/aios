from __future__ import annotations

from sqlalchemy import select

from infra_platform.models.cloud import CloudAccountModel, CloudResourceModel
from infra_platform.repositories.base import SQLAlchemyRepository


class CloudAccountRepository(SQLAlchemyRepository[CloudAccountModel]):
    model = CloudAccountModel

    async def list_for_tenant(self, tenant_id: str) -> list[CloudAccountModel]:
        stmt = select(CloudAccountModel).where(CloudAccountModel.tenant_id == tenant_id, CloudAccountModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_by_provider(self, tenant_id: str, provider: str) -> list[CloudAccountModel]:
        stmt = select(CloudAccountModel).where(
            CloudAccountModel.tenant_id == tenant_id, CloudAccountModel.provider == provider, CloudAccountModel.is_deleted.is_(False)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class CloudResourceRepository(SQLAlchemyRepository[CloudResourceModel]):
    model = CloudResourceModel

    async def list_for_account(self, tenant_id: str, cloud_account_id: str) -> list[CloudResourceModel]:
        stmt = select(CloudResourceModel).where(CloudResourceModel.tenant_id == tenant_id, CloudResourceModel.cloud_account_id == cloud_account_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_by_type(self, tenant_id: str, resource_type: str) -> list[CloudResourceModel]:
        stmt = select(CloudResourceModel).where(CloudResourceModel.tenant_id == tenant_id, CloudResourceModel.resource_type == resource_type)
        return list((await self.session.execute(stmt)).scalars().all())
