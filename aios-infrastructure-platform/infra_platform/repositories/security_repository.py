from __future__ import annotations

from sqlalchemy import select

from infra_platform.models.security import InfraRoleBindingModel, NetworkPolicyModel, RuntimePolicyModel
from infra_platform.repositories.base import SQLAlchemyRepository


class NetworkPolicyRepository(SQLAlchemyRepository[NetworkPolicyModel]):
    model = NetworkPolicyModel

    async def list_enabled(self, tenant_id: str) -> list[NetworkPolicyModel]:
        stmt = select(NetworkPolicyModel).where(
            NetworkPolicyModel.tenant_id == tenant_id, NetworkPolicyModel.is_deleted.is_(False), NetworkPolicyModel.is_enabled.is_(True)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class RuntimePolicyRepository(SQLAlchemyRepository[RuntimePolicyModel]):
    model = RuntimePolicyModel

    async def list_enabled(self, tenant_id: str) -> list[RuntimePolicyModel]:
        stmt = select(RuntimePolicyModel).where(
            RuntimePolicyModel.tenant_id == tenant_id, RuntimePolicyModel.is_deleted.is_(False), RuntimePolicyModel.is_enabled.is_(True)
        )
        return list((await self.session.execute(stmt)).scalars().all())


class InfraRoleBindingRepository(SQLAlchemyRepository[InfraRoleBindingModel]):
    model = InfraRoleBindingModel

    async def get_for_principal(self, tenant_id: str, principal_id: str, scope: str | None = None) -> InfraRoleBindingModel | None:
        stmt = select(InfraRoleBindingModel).where(
            InfraRoleBindingModel.tenant_id == tenant_id, InfraRoleBindingModel.principal_id == principal_id, InfraRoleBindingModel.scope == scope
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_principal(self, tenant_id: str, principal_id: str) -> list[InfraRoleBindingModel]:
        stmt = select(InfraRoleBindingModel).where(InfraRoleBindingModel.tenant_id == tenant_id, InfraRoleBindingModel.principal_id == principal_id)
        return list((await self.session.execute(stmt)).scalars().all())
