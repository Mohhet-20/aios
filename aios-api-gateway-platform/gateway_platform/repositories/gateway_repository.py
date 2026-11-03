from __future__ import annotations

from sqlalchemy import select

from gateway_platform.models.gateway import ApiRouteModel
from gateway_platform.repositories.base import SQLAlchemyRepository


class ApiRouteRepository(SQLAlchemyRepository[ApiRouteModel]):
    model = ApiRouteModel

    async def get_by_path_method(self, tenant_id: str, path: str, method: str) -> ApiRouteModel | None:
        stmt = select(ApiRouteModel).where(
            ApiRouteModel.tenant_id == tenant_id, ApiRouteModel.path == path, ApiRouteModel.method == method,
            ApiRouteModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str, *, status: str | None = None) -> list[ApiRouteModel]:
        stmt = select(ApiRouteModel).where(ApiRouteModel.tenant_id == tenant_id, ApiRouteModel.is_deleted.is_(False))
        if status:
            stmt = stmt.where(ApiRouteModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())
