from __future__ import annotations

from sqlalchemy import select

from prompt_platform.models.optimization import OptimizationRunModel, OptimizationSuggestionModel
from prompt_platform.repositories.base import SQLAlchemyRepository


class OptimizationRunRepository(SQLAlchemyRepository[OptimizationRunModel]):
    model = OptimizationRunModel

    async def list_for_prompt(self, prompt_id: str, *, limit: int = 50) -> list[OptimizationRunModel]:
        stmt = select(OptimizationRunModel).where(OptimizationRunModel.prompt_id == prompt_id).order_by(
            OptimizationRunModel.started_at.desc()
        ).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class OptimizationSuggestionRepository(SQLAlchemyRepository[OptimizationSuggestionModel]):
    model = OptimizationSuggestionModel

    async def list_for_run(self, optimization_run_id: str) -> list[OptimizationSuggestionModel]:
        stmt = select(OptimizationSuggestionModel).where(OptimizationSuggestionModel.optimization_run_id == optimization_run_id)
        return list((await self.session.execute(stmt)).scalars().all())
