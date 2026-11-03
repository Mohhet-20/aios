from __future__ import annotations

from sqlalchemy import select

from release_platform.models.environment import EnvironmentModel
from release_platform.repositories.base import SQLAlchemyRepository


class EnvironmentRepository(SQLAlchemyRepository[EnvironmentModel]):
    model = EnvironmentModel

    async def get_by_name(self, tenant_id: str, name: str) -> EnvironmentModel | None:
        stmt = select(EnvironmentModel).where(EnvironmentModel.tenant_id == tenant_id, EnvironmentModel.name == name)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str, *, environment_type: str | None = None) -> list[EnvironmentModel]:
        stmt = select(EnvironmentModel).where(EnvironmentModel.tenant_id == tenant_id)
        if environment_type:
            stmt = stmt.where(EnvironmentModel.environment_type == environment_type)
        return list((await self.session.execute(stmt)).scalars().all())
