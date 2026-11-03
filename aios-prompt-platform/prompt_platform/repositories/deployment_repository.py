from __future__ import annotations

from sqlalchemy import select

from prompt_platform.models.deployment import DeploymentEnvironmentConfigModel, DeploymentModel
from prompt_platform.repositories.base import SQLAlchemyRepository


class DeploymentRepository(SQLAlchemyRepository[DeploymentModel]):
    model = DeploymentModel

    async def list_for_prompt(self, prompt_id: str, *, environment: str | None = None) -> list[DeploymentModel]:
        stmt = select(DeploymentModel).where(DeploymentModel.prompt_id == prompt_id)
        if environment:
            stmt = stmt.where(DeploymentModel.environment == environment)
        stmt = stmt.order_by(DeploymentModel.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_current_for_environment(self, prompt_id: str, environment: str) -> DeploymentModel | None:
        stmt = (
            select(DeploymentModel)
            .where(
                DeploymentModel.prompt_id == prompt_id,
                DeploymentModel.environment == environment,
                DeploymentModel.status == "deployed",
            )
            .order_by(DeploymentModel.deployed_at.desc())
        )
        return (await self.session.execute(stmt)).scalars().first()


class DeploymentEnvironmentConfigRepository(SQLAlchemyRepository[DeploymentEnvironmentConfigModel]):
    model = DeploymentEnvironmentConfigModel

    async def get_for_workspace_env(self, workspace_id: str, environment: str) -> DeploymentEnvironmentConfigModel | None:
        stmt = select(DeploymentEnvironmentConfigModel).where(
            DeploymentEnvironmentConfigModel.workspace_id == workspace_id,
            DeploymentEnvironmentConfigModel.environment == environment,
        )
        return (await self.session.execute(stmt)).scalars().first()
