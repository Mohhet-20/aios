from __future__ import annotations

from sqlalchemy import select

from gateway_platform.models.traffic import TrafficRuleModel
from gateway_platform.repositories.base import SQLAlchemyRepository


class TrafficRuleRepository(SQLAlchemyRepository[TrafficRuleModel]):
    model = TrafficRuleModel

    async def list_for_route(self, tenant_id: str, route_id: str, *, status: str | None = None) -> list[TrafficRuleModel]:
        stmt = select(TrafficRuleModel).where(
            TrafficRuleModel.tenant_id == tenant_id, TrafficRuleModel.route_id == route_id,
            TrafficRuleModel.is_deleted.is_(False),
        ).order_by(TrafficRuleModel.priority.desc())
        if status:
            stmt = stmt.where(TrafficRuleModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())
