from __future__ import annotations

from sqlalchemy import select

from release_platform.models.license import LicenseModel
from release_platform.repositories.base import SQLAlchemyRepository


class LicenseRepository(SQLAlchemyRepository[LicenseModel]):
    model = LicenseModel

    async def list_for_org(self, tenant_id: str, org_ref: str) -> list[LicenseModel]:
        stmt = select(LicenseModel).where(LicenseModel.tenant_id == tenant_id, LicenseModel.org_ref == org_ref)
        return list((await self.session.execute(stmt)).scalars().all())
