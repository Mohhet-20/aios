from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select

from memory_platform.models.observability import ContextAssemblyLogModel, RetrievalLogModel
from memory_platform.repositories.base import SQLAlchemyRepository


class RetrievalLogRepository(SQLAlchemyRepository[RetrievalLogModel]):
    model = RetrievalLogModel

    async def list_for_workspace(self, workspace_id: str, *, since: datetime | None = None, limit: int = 500) -> list[RetrievalLogModel]:
        stmt = select(RetrievalLogModel).where(RetrievalLogModel.workspace_id == workspace_id)
        if since is not None:
            stmt = stmt.where(RetrievalLogModel.created_at >= since)
        stmt = stmt.order_by(RetrievalLogModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def failure_count(self, workspace_id: str) -> int:
        stmt = select(func.count()).where(RetrievalLogModel.workspace_id == workspace_id, RetrievalLogModel.success.is_(False))
        return (await self.session.execute(stmt)).scalar_one()


class ContextAssemblyLogRepository(SQLAlchemyRepository[ContextAssemblyLogModel]):
    model = ContextAssemblyLogModel

    async def list_for_workspace(self, workspace_id: str, *, limit: int = 500) -> list[ContextAssemblyLogModel]:
        stmt = select(ContextAssemblyLogModel).where(ContextAssemblyLogModel.workspace_id == workspace_id).order_by(ContextAssemblyLogModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
