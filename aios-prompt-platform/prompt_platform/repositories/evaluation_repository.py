from __future__ import annotations

from sqlalchemy import select

from prompt_platform.models.evaluation import EvaluationResultModel, EvaluationRunModel
from prompt_platform.repositories.base import SQLAlchemyRepository


class EvaluationRunRepository(SQLAlchemyRepository[EvaluationRunModel]):
    model = EvaluationRunModel

    async def list_for_prompt(self, prompt_id: str, *, limit: int = 50) -> list[EvaluationRunModel]:
        stmt = select(EvaluationRunModel).where(EvaluationRunModel.prompt_id == prompt_id).order_by(
            EvaluationRunModel.started_at.desc()
        ).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class EvaluationResultRepository(SQLAlchemyRepository[EvaluationResultModel]):
    model = EvaluationResultModel

    async def list_for_run(self, evaluation_run_id: str) -> list[EvaluationResultModel]:
        stmt = select(EvaluationResultModel).where(EvaluationResultModel.evaluation_run_id == evaluation_run_id)
        return list((await self.session.execute(stmt)).scalars().all())
