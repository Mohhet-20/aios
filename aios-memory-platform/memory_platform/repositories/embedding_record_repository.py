from __future__ import annotations

from sqlalchemy import func, select

from memory_platform.models.embedding_record import EmbeddingRecordModel
from memory_platform.repositories.base import SQLAlchemyRepository


class EmbeddingRecordRepository(SQLAlchemyRepository[EmbeddingRecordModel]):
    model = EmbeddingRecordModel

    async def get_for_source(self, source_type: str, source_id: str) -> EmbeddingRecordModel | None:
        stmt = select(EmbeddingRecordModel).where(
            EmbeddingRecordModel.source_type == source_type, EmbeddingRecordModel.source_id == source_id
        ).order_by(EmbeddingRecordModel.created_at.desc())
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_index(self, vector_store_index: str) -> list[EmbeddingRecordModel]:
        stmt = select(EmbeddingRecordModel).where(EmbeddingRecordModel.vector_store_index == vector_store_index)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_for_index(self, vector_store_index: str) -> int:
        stmt = select(func.count()).where(EmbeddingRecordModel.vector_store_index == vector_store_index)
        return (await self.session.execute(stmt)).scalar_one()

    async def distinct_dimensions_for_index(self, vector_store_index: str) -> list[int]:
        stmt = select(EmbeddingRecordModel.dimensions).where(EmbeddingRecordModel.vector_store_index == vector_store_index).distinct()
        return [row[0] for row in (await self.session.execute(stmt)).all()]

    async def list_distinct_indexes(self, workspace_id: str) -> list[str]:
        stmt = select(EmbeddingRecordModel.vector_store_index).where(EmbeddingRecordModel.workspace_id == workspace_id).distinct()
        return [row[0] for row in (await self.session.execute(stmt)).all()]

    async def list_for_sources(self, source_type: str, source_ids: list[str]) -> list[EmbeddingRecordModel]:
        if not source_ids:
            return []
        stmt = select(EmbeddingRecordModel).where(
            EmbeddingRecordModel.source_type == source_type, EmbeddingRecordModel.source_id.in_(source_ids)
        ).order_by(EmbeddingRecordModel.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_for_sources(self, source_type: str, source_ids: list[str]) -> int:
        records = await self.list_for_sources(source_type, source_ids)
        for r in records:
            await self.session.delete(r)
        if records:
            await self.session.flush()
        return len(records)
