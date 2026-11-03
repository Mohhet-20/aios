from __future__ import annotations

from sqlalchemy import select

from perf_platform.models.scalability import GpuPoolModel
from perf_platform.repositories.base import SQLAlchemyRepository


class GpuPoolRepository(SQLAlchemyRepository[GpuPoolModel]):
    model = GpuPoolModel

    async def get_by_name(self, tenant_id: str, name: str) -> GpuPoolModel | None:
        stmt = select(GpuPoolModel).where(GpuPoolModel.tenant_id == tenant_id, GpuPoolModel.name == name)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str, *, pool_type: str | None = None) -> list[GpuPoolModel]:
        stmt = select(GpuPoolModel).where(GpuPoolModel.tenant_id == tenant_id, GpuPoolModel.is_deleted.is_(False))
        if pool_type:
            stmt = stmt.where(GpuPoolModel.pool_type == pool_type)
        return list((await self.session.execute(stmt)).scalars().all())
