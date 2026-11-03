from __future__ import annotations

from sqlalchemy import or_, select

from memory_platform.models.knowledge_graph import KGEntityModel, KGRelationshipModel
from memory_platform.repositories.base import SQLAlchemyRepository


class KGEntityRepository(SQLAlchemyRepository[KGEntityModel]):
    model = KGEntityModel

    async def get_by_ref(self, workspace_id: str, entity_type: str, ref_id: str) -> KGEntityModel | None:
        stmt = select(KGEntityModel).where(
            KGEntityModel.workspace_id == workspace_id, KGEntityModel.entity_type == entity_type, KGEntityModel.ref_id == ref_id
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_by_type(self, workspace_id: str, entity_type: str) -> list[KGEntityModel]:
        return await self.list(filters={"workspace_id": workspace_id, "entity_type": entity_type})

    async def search_by_name(self, workspace_id: str, query: str, *, limit: int = 50) -> list[KGEntityModel]:
        from sqlalchemy import func
        pattern = f"%{query.lower()}%"
        stmt = select(KGEntityModel).where(KGEntityModel.workspace_id == workspace_id, func.lower(KGEntityModel.name).like(pattern)).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class KGRelationshipRepository(SQLAlchemyRepository[KGRelationshipModel]):
    model = KGRelationshipModel

    async def list_outgoing(self, entity_id: str, *, relation_type: str | None = None) -> list[KGRelationshipModel]:
        stmt = select(KGRelationshipModel).where(KGRelationshipModel.source_entity_id == entity_id)
        if relation_type:
            stmt = stmt.where(KGRelationshipModel.relation_type == relation_type)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_incoming(self, entity_id: str, *, relation_type: str | None = None) -> list[KGRelationshipModel]:
        stmt = select(KGRelationshipModel).where(KGRelationshipModel.target_entity_id == entity_id)
        if relation_type:
            stmt = stmt.where(KGRelationshipModel.relation_type == relation_type)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_touching(self, entity_id: str) -> list[KGRelationshipModel]:
        stmt = select(KGRelationshipModel).where(
            or_(KGRelationshipModel.source_entity_id == entity_id, KGRelationshipModel.target_entity_id == entity_id)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_workspace(self, workspace_id: str) -> list[KGRelationshipModel]:
        return await self.list(filters={"workspace_id": workspace_id})
