from __future__ import annotations

from sqlalchemy import select

from observability_platform.models.incidents import (
    IncidentModel,
    IncidentPostmortemModel,
    IncidentTimelineEventModel,
)
from observability_platform.repositories.base import SQLAlchemyRepository


class IncidentRepository(SQLAlchemyRepository[IncidentModel]):
    model = IncidentModel

    async def list_by_status(self, tenant_id: str, status: str, *, limit: int = 200) -> list[IncidentModel]:
        stmt = (
            select(IncidentModel)
            .where(IncidentModel.tenant_id == tenant_id, IncidentModel.status == status, IncidentModel.is_deleted.is_(False))
            .order_by(IncidentModel.detected_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_open(self, tenant_id: str, *, limit: int = 200) -> list[IncidentModel]:
        stmt = (
            select(IncidentModel)
            .where(
                IncidentModel.tenant_id == tenant_id,
                IncidentModel.is_deleted.is_(False),
                IncidentModel.status.notin_(["resolved", "closed"]),
            )
            .order_by(IncidentModel.detected_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_by_severity(self, tenant_id: str) -> dict[str, int]:
        from sqlalchemy import func

        stmt = (
            select(IncidentModel.severity, func.count())
            .where(IncidentModel.tenant_id == tenant_id, IncidentModel.is_deleted.is_(False))
            .group_by(IncidentModel.severity)
        )
        rows = (await self.session.execute(stmt)).all()
        return {sev: count for sev, count in rows}


class IncidentTimelineEventRepository(SQLAlchemyRepository[IncidentTimelineEventModel]):
    model = IncidentTimelineEventModel

    async def list_for_incident(self, tenant_id: str, incident_id: str) -> list[IncidentTimelineEventModel]:
        stmt = (
            select(IncidentTimelineEventModel)
            .where(
                IncidentTimelineEventModel.tenant_id == tenant_id,
                IncidentTimelineEventModel.incident_id == incident_id,
            )
            .order_by(IncidentTimelineEventModel.occurred_at.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())


class IncidentPostmortemRepository(SQLAlchemyRepository[IncidentPostmortemModel]):
    model = IncidentPostmortemModel

    async def get_for_incident(self, tenant_id: str, incident_id: str) -> IncidentPostmortemModel | None:
        stmt = select(IncidentPostmortemModel).where(
            IncidentPostmortemModel.tenant_id == tenant_id, IncidentPostmortemModel.incident_id == incident_id
        )
        return (await self.session.execute(stmt)).scalars().first()
