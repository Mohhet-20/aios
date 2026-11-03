from __future__ import annotations

from sqlalchemy import select

from observability_platform.models.topology import TopologyEdgeModel, TopologyNodeModel
from observability_platform.repositories.base import SQLAlchemyRepository


class TopologyNodeRepository(SQLAlchemyRepository[TopologyNodeModel]):
    model = TopologyNodeModel

    async def list_for_tenant(self, tenant_id: str) -> list[TopologyNodeModel]:
        stmt = select(TopologyNodeModel).where(
            TopologyNodeModel.tenant_id == tenant_id, TopologyNodeModel.is_deleted.is_(False)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class TopologyEdgeRepository(SQLAlchemyRepository[TopologyEdgeModel]):
    model = TopologyEdgeModel

    async def list_for_tenant(self, tenant_id: str) -> list[TopologyEdgeModel]:
        stmt = select(TopologyEdgeModel).where(
            TopologyEdgeModel.tenant_id == tenant_id, TopologyEdgeModel.is_deleted.is_(False)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_outgoing(self, tenant_id: str, source_node_id: str) -> list[TopologyEdgeModel]:
        stmt = select(TopologyEdgeModel).where(
            TopologyEdgeModel.tenant_id == tenant_id,
            TopologyEdgeModel.is_deleted.is_(False),
            TopologyEdgeModel.source_node_id == source_node_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_incoming(self, tenant_id: str, target_node_id: str) -> list[TopologyEdgeModel]:
        stmt = select(TopologyEdgeModel).where(
            TopologyEdgeModel.tenant_id == tenant_id,
            TopologyEdgeModel.is_deleted.is_(False),
            TopologyEdgeModel.target_node_id == target_node_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())
