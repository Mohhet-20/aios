from __future__ import annotations

from sqlalchemy import select

from gateway_platform.models.integrations import ConnectorModel, IntegrationConnectionModel
from gateway_platform.repositories.base import SQLAlchemyRepository


class ConnectorRepository(SQLAlchemyRepository[ConnectorModel]):
    model = ConnectorModel

    async def get_by_type(self, tenant_id: str, connector_type: str) -> ConnectorModel | None:
        stmt = select(ConnectorModel).where(
            ConnectorModel.tenant_id == tenant_id, ConnectorModel.connector_type == connector_type,
            ConnectorModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str) -> list[ConnectorModel]:
        stmt = select(ConnectorModel).where(ConnectorModel.tenant_id == tenant_id, ConnectorModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())


class IntegrationConnectionRepository(SQLAlchemyRepository[IntegrationConnectionModel]):
    model = IntegrationConnectionModel

    async def list_for_connector(self, tenant_id: str, connector_id: str) -> list[IntegrationConnectionModel]:
        stmt = select(IntegrationConnectionModel).where(
            IntegrationConnectionModel.tenant_id == tenant_id, IntegrationConnectionModel.connector_id == connector_id,
            IntegrationConnectionModel.is_deleted.is_(False),
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_tenant(self, tenant_id: str) -> list[IntegrationConnectionModel]:
        stmt = select(IntegrationConnectionModel).where(
            IntegrationConnectionModel.tenant_id == tenant_id, IntegrationConnectionModel.is_deleted.is_(False)
        )
        return list((await self.session.execute(stmt)).scalars().all())
