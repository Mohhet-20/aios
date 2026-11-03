from __future__ import annotations

from sqlalchemy import select

from release_platform.models.deployment import DeploymentModel
from release_platform.repositories.base import SQLAlchemyRepository


class DeploymentRepository(SQLAlchemyRepository[DeploymentModel]):
    model = DeploymentModel

    async def list_for_tenant(
        self, tenant_id: str, *, environment_id: str | None = None, status: str | None = None, limit: int = 100
    ) -> list[DeploymentModel]:
        stmt = select(DeploymentModel).where(DeploymentModel.tenant_id == tenant_id)
        if environment_id:
            stmt = stmt.where(DeploymentModel.environment_id == environment_id)
        if status:
            stmt = stmt.where(DeploymentModel.status == status)
        stmt = stmt.order_by(DeploymentModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
