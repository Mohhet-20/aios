from __future__ import annotations

from sqlalchemy import func, or_, select

from memory_platform.models.knowledge import (
    KnowledgeBaseModel,
    KnowledgeCollectionModel,
    KnowledgeItemModel,
    KnowledgeItemVersionModel,
)
from memory_platform.repositories.base import SQLAlchemyRepository


class KnowledgeBaseRepository(SQLAlchemyRepository[KnowledgeBaseModel]):
    model = KnowledgeBaseModel

    async def list_by_workspace(self, workspace_id: str) -> list[KnowledgeBaseModel]:
        return await self.list(filters={"workspace_id": workspace_id})


class KnowledgeCollectionRepository(SQLAlchemyRepository[KnowledgeCollectionModel]):
    model = KnowledgeCollectionModel

    async def list_by_knowledge_base(self, knowledge_base_id: str) -> list[KnowledgeCollectionModel]:
        return await self.list(filters={"knowledge_base_id": knowledge_base_id})


class KnowledgeItemRepository(SQLAlchemyRepository[KnowledgeItemModel]):
    model = KnowledgeItemModel

    async def list_by_knowledge_base(self, knowledge_base_id: str, *, status: str | None = None) -> list[KnowledgeItemModel]:
        filters = {"knowledge_base_id": knowledge_base_id}
        if status:
            filters["status"] = status
        return await self.list(filters=filters)

    async def list_by_collection(self, collection_id: str) -> list[KnowledgeItemModel]:
        return await self.list(filters={"collection_id": collection_id})

    async def search(self, workspace_id: str, query: str, *, status: str | None = None, limit: int = 50) -> list[KnowledgeItemModel]:
        pattern = f"%{query.lower()}%"
        stmt = select(KnowledgeItemModel).where(
            KnowledgeItemModel.workspace_id == workspace_id,
            or_(func.lower(KnowledgeItemModel.title).like(pattern), func.lower(KnowledgeItemModel.content).like(pattern)),
        )
        if status:
            stmt = stmt.where(KnowledgeItemModel.status == status)
        stmt = stmt.limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_many(self, ids: list[str]) -> list[KnowledgeItemModel]:
        if not ids:
            return []
        stmt = select(KnowledgeItemModel).where(KnowledgeItemModel.id.in_(ids))
        return list((await self.session.execute(stmt)).scalars().all())


    async def count_for_workspace(self, workspace_id: str, *, status: str | None = None) -> int:
        stmt = select(func.count()).where(KnowledgeItemModel.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(KnowledgeItemModel.status == status)
        return (await self.session.execute(stmt)).scalar_one()

    async def count_created_since(self, workspace_id: str, since) -> int:
        stmt = select(func.count()).where(KnowledgeItemModel.workspace_id == workspace_id, KnowledgeItemModel.created_at >= since)
        return (await self.session.execute(stmt)).scalar_one()


class KnowledgeItemVersionRepository(SQLAlchemyRepository[KnowledgeItemVersionModel]):
    model = KnowledgeItemVersionModel

    async def list_for_item(self, knowledge_item_id: str) -> list[KnowledgeItemVersionModel]:
        stmt = select(KnowledgeItemVersionModel).where(
            KnowledgeItemVersionModel.knowledge_item_id == knowledge_item_id
        ).order_by(KnowledgeItemVersionModel.version_number)
        return list((await self.session.execute(stmt)).scalars().all())
