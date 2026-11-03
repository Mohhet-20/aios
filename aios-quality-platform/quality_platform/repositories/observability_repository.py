from __future__ import annotations

from sqlalchemy import select

from quality_platform.models.observability import TrendSnapshotModel
from quality_platform.repositories.base import SQLAlchemyRepository


class TrendSnapshotRepository(SQLAlchemyRepository[TrendSnapshotModel]):
    model = TrendSnapshotModel

    async def list_for_metric(
        self, tenant_id: str, metric_type: str, *, subject_ref: str | None = None, limit: int = 500,
    ) -> list[TrendSnapshotModel]:
        stmt = select(TrendSnapshotModel).where(
            TrendSnapshotModel.tenant_id == tenant_id, TrendSnapshotModel.metric_type == metric_type,
        )
        if subject_ref:
            stmt = stmt.where(TrendSnapshotModel.subject_ref == subject_ref)
        stmt = stmt.order_by(TrendSnapshotModel.recorded_at.asc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
