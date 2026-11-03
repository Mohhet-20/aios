from __future__ import annotations

from sqlalchemy import select

from infra_platform.models.deployment import DeploymentEventModel, DeploymentModel, FeatureFlagModel, TrafficSplitModel
from infra_platform.repositories.base import SQLAlchemyRepository


class DeploymentRepository(SQLAlchemyRepository[DeploymentModel]):
    model = DeploymentModel

    async def list_for_service(self, tenant_id: str, service_id: str) -> list[DeploymentModel]:
        stmt = select(DeploymentModel).where(
            DeploymentModel.tenant_id == tenant_id, DeploymentModel.service_id == service_id
        ).order_by(DeploymentModel.started_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_by_status(self, tenant_id: str, status: str) -> list[DeploymentModel]:
        stmt = select(DeploymentModel).where(DeploymentModel.tenant_id == tenant_id, DeploymentModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_by_status(self, tenant_id: str) -> dict[str, int]:
        from sqlalchemy import func

        stmt = select(DeploymentModel.status, func.count()).where(DeploymentModel.tenant_id == tenant_id).group_by(DeploymentModel.status)
        rows = (await self.session.execute(stmt)).all()
        return {s: count for s, count in rows}


class TrafficSplitRepository(SQLAlchemyRepository[TrafficSplitModel]):
    model = TrafficSplitModel

    async def list_for_deployment(self, tenant_id: str, deployment_id: str) -> list[TrafficSplitModel]:
        stmt = select(TrafficSplitModel).where(
            TrafficSplitModel.tenant_id == tenant_id, TrafficSplitModel.deployment_id == deployment_id
        ).order_by(TrafficSplitModel.recorded_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())


class FeatureFlagRepository(SQLAlchemyRepository[FeatureFlagModel]):
    model = FeatureFlagModel

    async def get_by_key(self, tenant_id: str, key: str) -> FeatureFlagModel | None:
        stmt = select(FeatureFlagModel).where(FeatureFlagModel.tenant_id == tenant_id, FeatureFlagModel.key == key)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str) -> list[FeatureFlagModel]:
        stmt = select(FeatureFlagModel).where(FeatureFlagModel.tenant_id == tenant_id)
        return list((await self.session.execute(stmt)).scalars().all())


class DeploymentEventRepository(SQLAlchemyRepository[DeploymentEventModel]):
    model = DeploymentEventModel

    async def list_for_deployment(self, tenant_id: str, deployment_id: str) -> list[DeploymentEventModel]:
        stmt = select(DeploymentEventModel).where(
            DeploymentEventModel.tenant_id == tenant_id, DeploymentEventModel.deployment_id == deployment_id
        ).order_by(DeploymentEventModel.occurred_at.asc())
        return list((await self.session.execute(stmt)).scalars().all())
