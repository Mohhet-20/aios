from __future__ import annotations

from sqlalchemy import select

from gateway_platform.models.security import (
    GatewaySecurityPolicyModel,
    GeoRuleModel,
    IpRuleModel,
    SecurityEventModel,
)
from gateway_platform.repositories.base import SQLAlchemyRepository


class GatewaySecurityPolicyRepository(SQLAlchemyRepository[GatewaySecurityPolicyModel]):
    model = GatewaySecurityPolicyModel

    async def list_for_tenant(self, tenant_id: str, *, policy_type: str | None = None) -> list[GatewaySecurityPolicyModel]:
        stmt = select(GatewaySecurityPolicyModel).where(
            GatewaySecurityPolicyModel.tenant_id == tenant_id, GatewaySecurityPolicyModel.is_deleted.is_(False)
        )
        if policy_type:
            stmt = stmt.where(GatewaySecurityPolicyModel.policy_type == policy_type)
        return list((await self.session.execute(stmt)).scalars().all())


class IpRuleRepository(SQLAlchemyRepository[IpRuleModel]):
    model = IpRuleModel

    async def list_for_policy(self, tenant_id: str, policy_id: str) -> list[IpRuleModel]:
        stmt = select(IpRuleModel).where(IpRuleModel.tenant_id == tenant_id, IpRuleModel.policy_id == policy_id)
        return list((await self.session.execute(stmt)).scalars().all())


class GeoRuleRepository(SQLAlchemyRepository[GeoRuleModel]):
    model = GeoRuleModel

    async def list_for_policy(self, tenant_id: str, policy_id: str) -> list[GeoRuleModel]:
        stmt = select(GeoRuleModel).where(GeoRuleModel.tenant_id == tenant_id, GeoRuleModel.policy_id == policy_id)
        return list((await self.session.execute(stmt)).scalars().all())


class SecurityEventRepository(SQLAlchemyRepository[SecurityEventModel]):
    model = SecurityEventModel

    async def list_recent(self, tenant_id: str, *, severity: str | None = None, limit: int = 200) -> list[SecurityEventModel]:
        stmt = select(SecurityEventModel).where(SecurityEventModel.tenant_id == tenant_id)
        if severity:
            stmt = stmt.where(SecurityEventModel.severity == severity)
        stmt = stmt.order_by(SecurityEventModel.occurred_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
