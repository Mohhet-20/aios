from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select

from memory_platform.models.memory_entry import MemoryEntryModel
from memory_platform.repositories.base import SQLAlchemyRepository


class MemoryEntryRepository(SQLAlchemyRepository[MemoryEntryModel]):
    model = MemoryEntryModel

    async def list_for_scope(
        self, workspace_id: str, scope_type: str, scope_id: str, *, memory_type: str | None = None, status: str | None = None, limit: int = 200,
    ) -> list[MemoryEntryModel]:
        stmt = select(MemoryEntryModel).where(
            MemoryEntryModel.workspace_id == workspace_id, MemoryEntryModel.scope_type == scope_type, MemoryEntryModel.scope_id == scope_id,
        )
        if memory_type:
            stmt = stmt.where(MemoryEntryModel.memory_type == memory_type)
        if status:
            stmt = stmt.where(MemoryEntryModel.status == status)
        stmt = stmt.order_by(MemoryEntryModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_by_conversation(self, conversation_id: str) -> list[MemoryEntryModel]:
        stmt = select(MemoryEntryModel).where(MemoryEntryModel.conversation_id == conversation_id).order_by(MemoryEntryModel.turn_index)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_expired_candidates(self, workspace_id: str, *, as_of: datetime, status: str = "active") -> list[MemoryEntryModel]:
        stmt = select(MemoryEntryModel).where(
            MemoryEntryModel.workspace_id == workspace_id, MemoryEntryModel.status == status,
            MemoryEntryModel.expires_at.is_not(None), MemoryEntryModel.expires_at <= as_of,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_active_for_scope(self, workspace_id: str, memory_type: str, scope_type: str, scope_id: str) -> int:
        stmt = select(func.count()).where(
            MemoryEntryModel.workspace_id == workspace_id, MemoryEntryModel.memory_type == memory_type,
            MemoryEntryModel.scope_type == scope_type, MemoryEntryModel.scope_id == scope_id, MemoryEntryModel.status == "active",
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def search_keyword(self, workspace_id: str, query: str, *, memory_type: str | None = None, limit: int = 50) -> list[MemoryEntryModel]:
        pattern = f"%{query.lower()}%"
        stmt = select(MemoryEntryModel).where(
            MemoryEntryModel.workspace_id == workspace_id, MemoryEntryModel.status == "active",
            or_(func.lower(MemoryEntryModel.content).like(pattern), func.lower(MemoryEntryModel.title).like(pattern)),
        )
        if memory_type:
            stmt = stmt.where(MemoryEntryModel.memory_type == memory_type)
        stmt = stmt.limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_many(self, ids: list[str]) -> list[MemoryEntryModel]:
        if not ids:
            return []
        stmt = select(MemoryEntryModel).where(MemoryEntryModel.id.in_(ids))
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_older_than(
        self, workspace_id: str, cutoff: datetime, *, memory_type: str | None = None, scope_type: str | None = None, status: str = "active",
    ) -> list[MemoryEntryModel]:
        stmt = select(MemoryEntryModel).where(
            MemoryEntryModel.workspace_id == workspace_id, MemoryEntryModel.status == status, MemoryEntryModel.created_at <= cutoff,
        )
        if memory_type:
            stmt = stmt.where(MemoryEntryModel.memory_type == memory_type)
        if scope_type:
            stmt = stmt.where(MemoryEntryModel.scope_type == scope_type)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_for_workspace(self, workspace_id: str, *, status: str | None = None) -> int:
        stmt = select(func.count()).where(MemoryEntryModel.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(MemoryEntryModel.status == status)
        return (await self.session.execute(stmt)).scalar_one()

    async def sum_access_count_for_workspace(self, workspace_id: str) -> int:
        stmt = select(func.coalesce(func.sum(MemoryEntryModel.access_count), 0)).where(MemoryEntryModel.workspace_id == workspace_id)
        return (await self.session.execute(stmt)).scalar_one()

    async def count_created_since(self, workspace_id: str, since: datetime) -> int:
        stmt = select(func.count()).where(MemoryEntryModel.workspace_id == workspace_id, MemoryEntryModel.created_at >= since)
        return (await self.session.execute(stmt)).scalar_one()

    async def count_updated_since(self, workspace_id: str, since: datetime) -> int:
        stmt = select(func.count()).where(MemoryEntryModel.workspace_id == workspace_id, MemoryEntryModel.version > 1, MemoryEntryModel.updated_at >= since)
        return (await self.session.execute(stmt)).scalar_one()

    async def group_count_by_scope(self, workspace_id: str, scope_type: str) -> dict[str, dict]:
        stmt = (
            select(MemoryEntryModel.scope_id, func.count(), func.coalesce(func.sum(MemoryEntryModel.access_count), 0))
            .where(MemoryEntryModel.workspace_id == workspace_id, MemoryEntryModel.scope_type == scope_type)
            .group_by(MemoryEntryModel.scope_id)
        )
        rows = (await self.session.execute(stmt)).all()
        return {scope_id: {"entry_count": count, "total_access_count": access_sum} for scope_id, count, access_sum in rows}
