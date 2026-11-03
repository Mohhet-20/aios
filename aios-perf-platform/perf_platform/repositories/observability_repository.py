from __future__ import annotations

from sqlalchemy import select

from perf_platform.models.observability import BenchmarkRunModel, LatencySampleModel, ThroughputSampleModel
from perf_platform.repositories.base import SQLAlchemyRepository


class LatencySampleRepository(SQLAlchemyRepository[LatencySampleModel]):
    model = LatencySampleModel

    async def list_for_operation(self, tenant_id: str, operation: str, *, limit: int = 1000) -> list[LatencySampleModel]:
        stmt = select(LatencySampleModel).where(
            LatencySampleModel.tenant_id == tenant_id, LatencySampleModel.operation == operation,
        ).order_by(LatencySampleModel.recorded_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class ThroughputSampleRepository(SQLAlchemyRepository[ThroughputSampleModel]):
    model = ThroughputSampleModel

    async def list_for_operation(self, tenant_id: str, operation: str, *, limit: int = 1000) -> list[ThroughputSampleModel]:
        stmt = select(ThroughputSampleModel).where(
            ThroughputSampleModel.tenant_id == tenant_id, ThroughputSampleModel.operation == operation,
        ).order_by(ThroughputSampleModel.recorded_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class BenchmarkRunRepository(SQLAlchemyRepository[BenchmarkRunModel]):
    model = BenchmarkRunModel

    async def list_for_tenant(self, tenant_id: str, *, status: str | None = None) -> list[BenchmarkRunModel]:
        stmt = select(BenchmarkRunModel).where(BenchmarkRunModel.tenant_id == tenant_id, BenchmarkRunModel.is_deleted.is_(False))
        if status:
            stmt = stmt.where(BenchmarkRunModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())
