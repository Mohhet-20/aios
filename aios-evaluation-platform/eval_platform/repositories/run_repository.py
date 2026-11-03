from __future__ import annotations

from sqlalchemy import func, select

from eval_platform.models.run import EvaluationItemResultModel, EvaluationRunModel
from eval_platform.repositories.base import SQLAlchemyRepository


class EvaluationRunRepository(SQLAlchemyRepository[EvaluationRunModel]):
    model = EvaluationRunModel

    async def list_for_evaluation(self, evaluation_id: str, *, status: str | None = None, limit: int = 100) -> list[EvaluationRunModel]:
        stmt = select(EvaluationRunModel).where(EvaluationRunModel.evaluation_id == evaluation_id)
        if status:
            stmt = stmt.where(EvaluationRunModel.status == status)
        stmt = stmt.order_by(EvaluationRunModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_workspace(self, workspace_id: str, *, status: str | None = None, limit: int = 200) -> list[EvaluationRunModel]:
        stmt = select(EvaluationRunModel).where(EvaluationRunModel.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(EvaluationRunModel.status == status)
        stmt = stmt.order_by(EvaluationRunModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_active_for_workspace(self, workspace_id: str) -> int:
        stmt = select(func.count()).where(
            EvaluationRunModel.workspace_id == workspace_id, EvaluationRunModel.status.in_(["pending", "running"]),
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def count_recent_by_triggerer(self, triggered_by: str, *, since) -> int:
        stmt = select(func.count()).where(
            EvaluationRunModel.triggered_by == triggered_by, EvaluationRunModel.created_at >= since,
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def list_stalled_running(self, *, older_than) -> list[EvaluationRunModel]:
        stmt = select(EvaluationRunModel).where(
            EvaluationRunModel.status == "running", EvaluationRunModel.started_at.is_not(None),
            EvaluationRunModel.started_at <= older_than,
        )
        return list((await self.session.execute(stmt)).scalars().all())


class EvaluationItemResultRepository(SQLAlchemyRepository[EvaluationItemResultModel]):
    model = EvaluationItemResultModel

    async def list_for_run(self, run_id: str) -> list[EvaluationItemResultModel]:
        stmt = select(EvaluationItemResultModel).where(EvaluationItemResultModel.run_id == run_id)
        return list((await self.session.execute(stmt)).scalars().all())
