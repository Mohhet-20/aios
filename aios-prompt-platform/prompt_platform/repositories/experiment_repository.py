from __future__ import annotations

from sqlalchemy import select

from prompt_platform.models.experiment import ExperimentModel, ExperimentResultModel, ExperimentVariantModel
from prompt_platform.repositories.base import SQLAlchemyRepository


class ExperimentRepository(SQLAlchemyRepository[ExperimentModel]):
    model = ExperimentModel

    async def list_for_workspace(self, workspace_id: str) -> list[ExperimentModel]:
        return await self.list(filters={"workspace_id": workspace_id})


class ExperimentVariantRepository(SQLAlchemyRepository[ExperimentVariantModel]):
    model = ExperimentVariantModel

    async def list_for_experiment(self, experiment_id: str) -> list[ExperimentVariantModel]:
        stmt = select(ExperimentVariantModel).where(ExperimentVariantModel.experiment_id == experiment_id)
        return list((await self.session.execute(stmt)).scalars().all())


class ExperimentResultRepository(SQLAlchemyRepository[ExperimentResultModel]):
    model = ExperimentResultModel

    async def list_for_experiment(self, experiment_id: str) -> list[ExperimentResultModel]:
        stmt = select(ExperimentResultModel).where(ExperimentResultModel.experiment_id == experiment_id)
        return list((await self.session.execute(stmt)).scalars().all())
