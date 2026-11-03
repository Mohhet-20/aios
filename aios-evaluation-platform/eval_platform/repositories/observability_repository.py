from __future__ import annotations

from sqlalchemy import select

from eval_platform.models.observability import ObservabilityEventModel
from eval_platform.repositories.base import SQLAlchemyRepository


class ObservabilityEventRepository(SQLAlchemyRepository[ObservabilityEventModel]):
    model = ObservabilityEventModel

    async def list_for_workspace(
        self, workspace_id: str, *, event_type: str | None = None, source_execution_id: str | None = None, limit: int = 500
    ) -> list[ObservabilityEventModel]:
        stmt = select(ObservabilityEventModel).where(ObservabilityEventModel.workspace_id == workspace_id)
        if event_type:
            stmt = stmt.where(ObservabilityEventModel.event_type == event_type)
        if source_execution_id:
            stmt = stmt.where(ObservabilityEventModel.source_execution_id == source_execution_id)
        stmt = stmt.order_by(ObservabilityEventModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_since(self, workspace_id: str, *, since) -> list[ObservabilityEventModel]:
        stmt = select(ObservabilityEventModel).where(
            ObservabilityEventModel.workspace_id == workspace_id, ObservabilityEventModel.created_at >= since,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_older_than(self, *, older_than, limit: int = 1000) -> list[ObservabilityEventModel]:
        """Backs the retention-policy sweep — rows past the configured
        retention window, oldest ingestion first, batched to `limit`."""
        stmt = select(ObservabilityEventModel).where(ObservabilityEventModel.created_at < older_than).order_by(ObservabilityEventModel.created_at).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
