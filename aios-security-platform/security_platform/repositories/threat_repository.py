from __future__ import annotations

from sqlalchemy import select

from security_platform.models.threats import ThreatDetectionModel
from security_platform.repositories.base import SQLAlchemyRepository


class ThreatDetectionRepository(SQLAlchemyRepository[ThreatDetectionModel]):
    model = ThreatDetectionModel

    async def list_by_status(self, tenant_id: str, status: str, *, limit: int = 200) -> list[ThreatDetectionModel]:
        stmt = (
            select(ThreatDetectionModel)
            .where(ThreatDetectionModel.tenant_id == tenant_id, ThreatDetectionModel.status == status)
            .order_by(ThreatDetectionModel.detected_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_by_type(self, tenant_id: str, *, start_time=None) -> dict[str, int]:
        from sqlalchemy import func

        stmt = select(ThreatDetectionModel.threat_type, func.count()).where(ThreatDetectionModel.tenant_id == tenant_id)
        if start_time is not None:
            stmt = stmt.where(ThreatDetectionModel.detected_at >= start_time)
        stmt = stmt.group_by(ThreatDetectionModel.threat_type)
        rows = (await self.session.execute(stmt)).all()
        return {t: count for t, count in rows}

    async def count_by_status(self, tenant_id: str) -> dict[str, int]:
        from sqlalchemy import func

        stmt = (
            select(ThreatDetectionModel.status, func.count())
            .where(ThreatDetectionModel.tenant_id == tenant_id)
            .group_by(ThreatDetectionModel.status)
        )
        rows = (await self.session.execute(stmt)).all()
        return {s: count for s, count in rows}
