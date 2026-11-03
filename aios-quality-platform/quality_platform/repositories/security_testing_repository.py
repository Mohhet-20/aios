from __future__ import annotations

from sqlalchemy import select

from quality_platform.models.security_testing import SecurityFindingModel, SecurityScanModel
from quality_platform.repositories.base import SQLAlchemyRepository


class SecurityScanRepository(SQLAlchemyRepository[SecurityScanModel]):
    model = SecurityScanModel

    async def list_for_tenant(self, tenant_id: str, *, security_test_type: str | None = None, limit: int = 100) -> list[SecurityScanModel]:
        stmt = select(SecurityScanModel).where(SecurityScanModel.tenant_id == tenant_id)
        if security_test_type:
            stmt = stmt.where(SecurityScanModel.security_test_type == security_test_type)
        stmt = stmt.order_by(SecurityScanModel.requested_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class SecurityFindingRepository(SQLAlchemyRepository[SecurityFindingModel]):
    model = SecurityFindingModel

    async def list_for_scan(self, tenant_id: str, security_scan_id: str) -> list[SecurityFindingModel]:
        stmt = select(SecurityFindingModel).where(
            SecurityFindingModel.tenant_id == tenant_id, SecurityFindingModel.security_scan_id == security_scan_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())
