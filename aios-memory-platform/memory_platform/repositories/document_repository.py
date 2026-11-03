from __future__ import annotations

from sqlalchemy import select

from memory_platform.models.document import DocumentChunkModel, DocumentModel
from memory_platform.repositories.base import SQLAlchemyRepository


class DocumentRepository(SQLAlchemyRepository[DocumentModel]):
    model = DocumentModel

    async def list_by_workspace(self, workspace_id: str, *, status: str | None = None) -> list[DocumentModel]:
        filters = {"workspace_id": workspace_id}
        if status:
            filters["status"] = status
        return await self.list(filters=filters)

    async def list_by_knowledge_base(self, knowledge_base_id: str) -> list[DocumentModel]:
        return await self.list(filters={"knowledge_base_id": knowledge_base_id})


    async def sum_size_bytes(self, workspace_id: str) -> int:
        from sqlalchemy import func
        stmt = select(func.coalesce(func.sum(DocumentModel.size_bytes), 0)).where(DocumentModel.workspace_id == workspace_id)
        return (await self.session.execute(stmt)).scalar_one()

    async def count_total(self, workspace_id: str, *, status: str | None = None) -> int:
        from sqlalchemy import func
        stmt = select(func.count()).where(DocumentModel.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(DocumentModel.status == status)
        return (await self.session.execute(stmt)).scalar_one()


class DocumentChunkRepository(SQLAlchemyRepository[DocumentChunkModel]):
    model = DocumentChunkModel

    async def list_for_document(self, document_id: str) -> list[DocumentChunkModel]:
        stmt = select(DocumentChunkModel).where(DocumentChunkModel.document_id == document_id).order_by(DocumentChunkModel.chunk_index)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_many(self, ids: list[str]) -> list[DocumentChunkModel]:
        if not ids:
            return []
        stmt = select(DocumentChunkModel).where(DocumentChunkModel.id.in_(ids))
        return list((await self.session.execute(stmt)).scalars().all())
