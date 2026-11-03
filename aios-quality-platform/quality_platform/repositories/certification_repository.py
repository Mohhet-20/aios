from __future__ import annotations

from sqlalchemy import select

from quality_platform.models.certification import CertificationRunModel
from quality_platform.repositories.base import SQLAlchemyRepository


class CertificationRunRepository(SQLAlchemyRepository[CertificationRunModel]):
    model = CertificationRunModel

    async def list_for_release(self, tenant_id: str, release_ref: str, *, limit: int = 50) -> list[CertificationRunModel]:
        stmt = select(CertificationRunModel).where(
            CertificationRunModel.tenant_id == tenant_id, CertificationRunModel.release_ref == release_ref,
        ).order_by(CertificationRunModel.requested_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
