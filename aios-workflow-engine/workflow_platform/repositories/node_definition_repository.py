from __future__ import annotations

from sqlalchemy import select

from workflow_platform.models.node_definition import NodeDefinitionModel
from workflow_platform.repositories.base import SQLAlchemyRepository


class NodeDefinitionRepository(SQLAlchemyRepository[NodeDefinitionModel]):
    model = NodeDefinitionModel

    async def get_by_key(self, key: str) -> NodeDefinitionModel | None:
        stmt = select(NodeDefinitionModel).where(NodeDefinitionModel.key == key)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_all(self) -> list[NodeDefinitionModel]:
        stmt = select(NodeDefinitionModel).order_by(NodeDefinitionModel.category, NodeDefinitionModel.key)
        return list((await self.session.execute(stmt)).scalars().all())
