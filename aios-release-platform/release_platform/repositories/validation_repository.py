from __future__ import annotations

from sqlalchemy import select

from release_platform.models.validation import HealthCheckRunModel
from release_platform.repositories.base import SQLAlchemyRepository


class HealthCheckRunRepository(SQLAlchemyRepository[HealthCheckRunModel]):
    model = HealthCheckRunModel

    async def list_for_deployment(self, tenant_id: str, deployment_id: str) -> list[HealthCheckRunModel]:
        stmt = select(HealthCheckRunModel).where(
            HealthCheckRunModel.tenant_id == tenant_id, HealthCheckRunModel.deployment_id == deployment_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())
