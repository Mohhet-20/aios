from __future__ import annotations

from sqlalchemy import select

from security_platform.models.policies import PolicyExceptionModel, PolicyModel, PolicyVersionModel
from security_platform.repositories.base import SQLAlchemyRepository


class PolicyRepository(SQLAlchemyRepository[PolicyModel]):
    model = PolicyModel

    async def list_for_scope(self, tenant_id: str, scope: str, *, scope_ref_id: str | None = None) -> list[PolicyModel]:
        stmt = select(PolicyModel).where(
            PolicyModel.tenant_id == tenant_id, PolicyModel.scope == scope, PolicyModel.is_deleted.is_(False)
        )
        if scope_ref_id is not None:
            stmt = stmt.where(PolicyModel.scope_ref_id == scope_ref_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_active_for_tenant(self, tenant_id: str) -> list[PolicyModel]:
        stmt = select(PolicyModel).where(
            PolicyModel.tenant_id == tenant_id, PolicyModel.is_deleted.is_(False), PolicyModel.status == "active"
        )
        return list((await self.session.execute(stmt)).scalars().all())


class PolicyVersionRepository(SQLAlchemyRepository[PolicyVersionModel]):
    model = PolicyVersionModel

    async def list_for_policy(self, tenant_id: str, policy_id: str) -> list[PolicyVersionModel]:
        stmt = (
            select(PolicyVersionModel)
            .where(PolicyVersionModel.tenant_id == tenant_id, PolicyVersionModel.policy_id == policy_id)
            .order_by(PolicyVersionModel.version_number.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())


class PolicyExceptionRepository(SQLAlchemyRepository[PolicyExceptionModel]):
    model = PolicyExceptionModel

    async def list_active_for_policy(self, tenant_id: str, policy_id: str) -> list[PolicyExceptionModel]:
        stmt = select(PolicyExceptionModel).where(
            PolicyExceptionModel.tenant_id == tenant_id,
            PolicyExceptionModel.policy_id == policy_id,
            PolicyExceptionModel.is_deleted.is_(False),
        )
        return list((await self.session.execute(stmt)).scalars().all())
