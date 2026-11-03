from __future__ import annotations

from sqlalchemy import select

from analytics_platform.models.exports import DataExportJobModel
from analytics_platform.repositories.base import SQLAlchemyRepository


class DataExportJobRepository(SQLAlchemyRepository[DataExportJobModel]):
    model = DataExportJobModel

    async def list_for_tenant(self, tenant_id: str, *, resource_type: str | None = None) -> list[DataExportJobModel]:
        stmt = select(DataExportJobModel).where(DataExportJobModel.tenant_id == tenant_id)
        if resource_type:
            stmt = stmt.where(DataExportJobModel.resource_type == resource_type)
        return list((await self.session.execute(stmt)).scalars().all())
