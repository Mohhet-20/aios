from __future__ import annotations

from sqlalchemy import select

from infra_platform.models.services import ServiceModel
from infra_platform.repositories.base import SQLAlchemyRepository


class ServiceRepository(SQLAlchemyRepository[ServiceModel]):
    model = ServiceModel

    async def list_for_tenant(self, tenant_id: str) -> list[ServiceModel]:
        stmt = select(ServiceModel).where(ServiceModel.tenant_id == tenant_id, ServiceModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_by_type(self, tenant_id: str, service_type: str) -> list[ServiceModel]:
        stmt = select(ServiceModel).where(
            ServiceModel.tenant_id == tenant_id, ServiceModel.service_type == service_type, ServiceModel.is_deleted.is_(False)
        )
        return list((await self.session.execute(stmt)).scalars().all())
