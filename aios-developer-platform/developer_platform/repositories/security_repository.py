from __future__ import annotations

from sqlalchemy import select

from developer_platform.models.security import DeveloperRoleBindingModel, SecretReferenceModel
from developer_platform.repositories.base import SQLAlchemyRepository


class DeveloperRoleBindingRepository(SQLAlchemyRepository[DeveloperRoleBindingModel]):
    model = DeveloperRoleBindingModel

    async def get_for_principal(self, tenant_id: str, principal_id: str, scope: str | None = None) -> DeveloperRoleBindingModel | None:
        stmt = select(DeveloperRoleBindingModel).where(
            DeveloperRoleBindingModel.tenant_id == tenant_id, DeveloperRoleBindingModel.principal_id == principal_id,
            DeveloperRoleBindingModel.scope == scope,
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_principal(self, tenant_id: str, principal_id: str) -> list[DeveloperRoleBindingModel]:
        stmt = select(DeveloperRoleBindingModel).where(
            DeveloperRoleBindingModel.tenant_id == tenant_id, DeveloperRoleBindingModel.principal_id == principal_id
        )
        return list((await self.session.execute(stmt)).scalars().all())


class SecretReferenceRepository(SQLAlchemyRepository[SecretReferenceModel]):
    model = SecretReferenceModel

    async def get_by_name(self, tenant_id: str, name: str) -> SecretReferenceModel | None:
        stmt = select(SecretReferenceModel).where(
            SecretReferenceModel.tenant_id == tenant_id, SecretReferenceModel.name == name
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_by_type(self, tenant_id: str, reference_type: str) -> list[SecretReferenceModel]:
        stmt = select(SecretReferenceModel).where(
            SecretReferenceModel.tenant_id == tenant_id, SecretReferenceModel.reference_type == reference_type
        )
        return list((await self.session.execute(stmt)).scalars().all())
