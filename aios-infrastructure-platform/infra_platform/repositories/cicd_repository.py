from __future__ import annotations

from sqlalchemy import select

from infra_platform.models.cicd import DeploymentGateModel, PipelineModel, PipelineRunModel, PipelineStageRunModel, ReleaseModel
from infra_platform.repositories.base import SQLAlchemyRepository


class PipelineRepository(SQLAlchemyRepository[PipelineModel]):
    model = PipelineModel

    async def get_by_name(self, tenant_id: str, name: str) -> PipelineModel | None:
        stmt = select(PipelineModel).where(PipelineModel.tenant_id == tenant_id, PipelineModel.name == name, PipelineModel.is_deleted.is_(False))
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str) -> list[PipelineModel]:
        stmt = select(PipelineModel).where(PipelineModel.tenant_id == tenant_id, PipelineModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())


class PipelineRunRepository(SQLAlchemyRepository[PipelineRunModel]):
    model = PipelineRunModel

    async def list_for_pipeline(self, tenant_id: str, pipeline_id: str, *, limit: int = 200) -> list[PipelineRunModel]:
        stmt = select(PipelineRunModel).where(
            PipelineRunModel.tenant_id == tenant_id, PipelineRunModel.pipeline_id == pipeline_id
        ).order_by(PipelineRunModel.started_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_by_status(self, tenant_id: str, status: str) -> list[PipelineRunModel]:
        stmt = select(PipelineRunModel).where(PipelineRunModel.tenant_id == tenant_id, PipelineRunModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())


class PipelineStageRunRepository(SQLAlchemyRepository[PipelineStageRunModel]):
    model = PipelineStageRunModel

    async def list_for_run(self, tenant_id: str, run_id: str) -> list[PipelineStageRunModel]:
        stmt = select(PipelineStageRunModel).where(
            PipelineStageRunModel.tenant_id == tenant_id, PipelineStageRunModel.run_id == run_id
        ).order_by(PipelineStageRunModel.started_at.asc())
        return list((await self.session.execute(stmt)).scalars().all())


class DeploymentGateRepository(SQLAlchemyRepository[DeploymentGateModel]):
    model = DeploymentGateModel

    async def list_for_run(self, tenant_id: str, pipeline_run_id: str) -> list[DeploymentGateModel]:
        stmt = select(DeploymentGateModel).where(
            DeploymentGateModel.tenant_id == tenant_id, DeploymentGateModel.pipeline_run_id == pipeline_run_id
        )
        return list((await self.session.execute(stmt)).scalars().all())


class ReleaseRepository(SQLAlchemyRepository[ReleaseModel]):
    model = ReleaseModel

    async def get_by_name_version(self, tenant_id: str, name: str, version: str) -> ReleaseModel | None:
        stmt = select(ReleaseModel).where(ReleaseModel.tenant_id == tenant_id, ReleaseModel.name == name, ReleaseModel.version == version)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str) -> list[ReleaseModel]:
        stmt = select(ReleaseModel).where(ReleaseModel.tenant_id == tenant_id).order_by(ReleaseModel.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())
