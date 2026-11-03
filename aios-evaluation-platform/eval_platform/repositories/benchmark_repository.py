from __future__ import annotations

from sqlalchemy import select

from eval_platform.models.benchmark import BenchmarkCandidateResultModel, BenchmarkModel, BenchmarkRunModel
from eval_platform.repositories.base import SQLAlchemyRepository


class BenchmarkRepository(SQLAlchemyRepository[BenchmarkModel]):
    model = BenchmarkModel

    async def list_for_workspace(self, workspace_id: str, *, benchmark_type: str | None = None) -> list[BenchmarkModel]:
        stmt = select(BenchmarkModel).where(BenchmarkModel.workspace_id == workspace_id, BenchmarkModel.is_deleted.is_(False))
        if benchmark_type:
            stmt = stmt.where(BenchmarkModel.benchmark_type == benchmark_type)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_slug(self, workspace_id: str, slug: str) -> BenchmarkModel | None:
        stmt = select(BenchmarkModel).where(BenchmarkModel.workspace_id == workspace_id, BenchmarkModel.slug == slug, BenchmarkModel.is_deleted.is_(False))
        return (await self.session.execute(stmt)).scalars().first()


class BenchmarkRunRepository(SQLAlchemyRepository[BenchmarkRunModel]):
    model = BenchmarkRunModel

    async def list_for_benchmark(self, benchmark_id: str, *, limit: int = 100) -> list[BenchmarkRunModel]:
        stmt = select(BenchmarkRunModel).where(BenchmarkRunModel.benchmark_id == benchmark_id).order_by(BenchmarkRunModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class BenchmarkCandidateResultRepository(SQLAlchemyRepository[BenchmarkCandidateResultModel]):
    model = BenchmarkCandidateResultModel

    async def list_for_run(self, benchmark_run_id: str) -> list[BenchmarkCandidateResultModel]:
        stmt = select(BenchmarkCandidateResultModel).where(BenchmarkCandidateResultModel.benchmark_run_id == benchmark_run_id)
        return list((await self.session.execute(stmt)).scalars().all())
