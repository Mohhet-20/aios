from __future__ import annotations

from sqlalchemy import select

from perf_platform.models.routing import RoutingDecisionModel, RoutingPolicyModel
from perf_platform.repositories.base import SQLAlchemyRepository


class RoutingPolicyRepository(SQLAlchemyRepository[RoutingPolicyModel]):
    model = RoutingPolicyModel

    async def get_for_scope(self, tenant_id: str, scope_type: str, scope_id: str) -> RoutingPolicyModel | None:
        stmt = select(RoutingPolicyModel).where(
            RoutingPolicyModel.tenant_id == tenant_id, RoutingPolicyModel.scope_type == scope_type,
            RoutingPolicyModel.scope_id == scope_id, RoutingPolicyModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()


class RoutingDecisionRepository(SQLAlchemyRepository[RoutingDecisionModel]):
    model = RoutingDecisionModel

    async def list_for_tenant(self, tenant_id: str, *, limit: int = 100) -> list[RoutingDecisionModel]:
        stmt = select(RoutingDecisionModel).where(RoutingDecisionModel.tenant_id == tenant_id).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
