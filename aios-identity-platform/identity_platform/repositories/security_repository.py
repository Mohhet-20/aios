from __future__ import annotations

from sqlalchemy import select

from identity_platform.models.security import SecurityEventModel, SecurityPolicyModel
from identity_platform.repositories.base import SQLAlchemyRepository


class SecurityPolicyRepository(SQLAlchemyRepository[SecurityPolicyModel]):
    model = SecurityPolicyModel

    async def list_for_organization(self, organization_id: str | None, *, policy_type: str | None = None) -> list[SecurityPolicyModel]:
        stmt = select(SecurityPolicyModel).where(SecurityPolicyModel.organization_id == organization_id)
        if policy_type:
            stmt = stmt.where(SecurityPolicyModel.policy_type == policy_type)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_effective(self, organization_id: str | None, policy_type: str) -> SecurityPolicyModel | None:
        """Org-specific policy if one exists, else the global default (organization_id is null)."""
        stmt = select(SecurityPolicyModel).where(
            SecurityPolicyModel.policy_type == policy_type, SecurityPolicyModel.organization_id == organization_id,
        )
        result = (await self.session.execute(stmt)).scalars().first()
        if result is not None or organization_id is None:
            return result
        stmt = select(SecurityPolicyModel).where(
            SecurityPolicyModel.policy_type == policy_type, SecurityPolicyModel.organization_id.is_(None),
        )
        return (await self.session.execute(stmt)).scalars().first()


class SecurityEventRepository(SQLAlchemyRepository[SecurityEventModel]):
    model = SecurityEventModel

    async def list_for_user(self, user_id: str, *, limit: int = 50) -> list[SecurityEventModel]:
        stmt = select(SecurityEventModel).where(SecurityEventModel.user_id == user_id).order_by(SecurityEventModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_organization(self, organization_id: str, *, severity: str | None = None, limit: int = 100) -> list[SecurityEventModel]:
        stmt = select(SecurityEventModel).where(SecurityEventModel.organization_id == organization_id)
        if severity:
            stmt = stmt.where(SecurityEventModel.severity == severity)
        stmt = stmt.order_by(SecurityEventModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_unresolved(self, organization_id: str | None = None) -> list[SecurityEventModel]:
        stmt = select(SecurityEventModel).where(SecurityEventModel.resolved.is_(False))
        if organization_id:
            stmt = stmt.where(SecurityEventModel.organization_id == organization_id)
        return list((await self.session.execute(stmt)).scalars().all())
