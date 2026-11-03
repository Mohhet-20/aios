from __future__ import annotations

from sqlalchemy import select

from quality_platform.models.performance import BenchmarkResultModel, PerformanceTestRunModel
from quality_platform.repositories.base import SQLAlchemyRepository


class PerformanceTestRunRepository(SQLAlchemyRepository[PerformanceTestRunModel]):
    model = PerformanceTestRunModel

    async def list_for_tenant(
        self, tenant_id: str, *, performance_test_type: str | None = None, limit: int = 100,
    ) -> list[PerformanceTestRunModel]:
        stmt = select(PerformanceTestRunModel).where(PerformanceTestRunModel.tenant_id == tenant_id)
        if performance_test_type:
            stmt = stmt.where(PerformanceTestRunModel.performance_test_type == performance_test_type)
        stmt = stmt.order_by(PerformanceTestRunModel.requested_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class BenchmarkResultRepository(SQLAlchemyRepository[BenchmarkResultModel]):
    model = BenchmarkResultModel

    async def list_for_run(self, tenant_id: str, performance_test_run_id: str) -> list[BenchmarkResultModel]:
        stmt = select(BenchmarkResultModel).where(
            BenchmarkResultModel.tenant_id == tenant_id, BenchmarkResultModel.performance_test_run_id == performance_test_run_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())
