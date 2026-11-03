from __future__ import annotations

from sqlalchemy import select

from infra_platform.models.experiments import ExperimentModel, ExperimentRunModel, RunMetricModel, RunParamModel
from infra_platform.repositories.base import SQLAlchemyRepository


class ExperimentRepository(SQLAlchemyRepository[ExperimentModel]):
    model = ExperimentModel

    async def get_by_name(self, tenant_id: str, name: str) -> ExperimentModel | None:
        stmt = select(ExperimentModel).where(ExperimentModel.tenant_id == tenant_id, ExperimentModel.name == name, ExperimentModel.is_deleted.is_(False))
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str) -> list[ExperimentModel]:
        stmt = select(ExperimentModel).where(ExperimentModel.tenant_id == tenant_id, ExperimentModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())


class ExperimentRunRepository(SQLAlchemyRepository[ExperimentRunModel]):
    model = ExperimentRunModel

    async def list_for_experiment(self, tenant_id: str, experiment_id: str) -> list[ExperimentRunModel]:
        stmt = select(ExperimentRunModel).where(
            ExperimentRunModel.tenant_id == tenant_id, ExperimentRunModel.experiment_id == experiment_id
        ).order_by(ExperimentRunModel.started_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())


class RunMetricRepository(SQLAlchemyRepository[RunMetricModel]):
    model = RunMetricModel

    async def list_for_run(self, tenant_id: str, run_id: str) -> list[RunMetricModel]:
        stmt = select(RunMetricModel).where(RunMetricModel.tenant_id == tenant_id, RunMetricModel.run_id == run_id).order_by(RunMetricModel.step.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_run_key(self, tenant_id: str, run_id: str, key: str) -> list[RunMetricModel]:
        stmt = select(RunMetricModel).where(
            RunMetricModel.tenant_id == tenant_id, RunMetricModel.run_id == run_id, RunMetricModel.key == key
        ).order_by(RunMetricModel.step.asc())
        return list((await self.session.execute(stmt)).scalars().all())


class RunParamRepository(SQLAlchemyRepository[RunParamModel]):
    model = RunParamModel

    async def list_for_run(self, tenant_id: str, run_id: str) -> list[RunParamModel]:
        stmt = select(RunParamModel).where(RunParamModel.tenant_id == tenant_id, RunParamModel.run_id == run_id)
        return list((await self.session.execute(stmt)).scalars().all())
