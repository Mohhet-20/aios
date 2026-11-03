from __future__ import annotations

from sqlalchemy import select

from identity_platform.models.rbac import PermissionModel, RoleAssignmentModel, RoleModel
from identity_platform.repositories.base import SQLAlchemyRepository


class RoleRepository(SQLAlchemyRepository[RoleModel]):
    model = RoleModel

    async def get_by_slug(self, organization_id: str | None, slug: str) -> RoleModel | None:
        stmt = select(RoleModel).where(RoleModel.organization_id == organization_id, RoleModel.slug == slug)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_available_for_organization(self, organization_id: str) -> list[RoleModel]:
        """Built-in system roles (organization_id is null) plus any
        custom roles this organization has defined."""
        stmt = select(RoleModel).where((RoleModel.organization_id == organization_id) | (RoleModel.organization_id.is_(None)))
        return list((await self.session.execute(stmt)).scalars().all())


class RoleAssignmentRepository(SQLAlchemyRepository[RoleAssignmentModel]):
    model = RoleAssignmentModel

    async def list_for_principal(self, principal_type: str, principal_id: str, *, active_only: bool = True) -> list[RoleAssignmentModel]:
        stmt = select(RoleAssignmentModel).where(
            RoleAssignmentModel.principal_type == principal_type, RoleAssignmentModel.principal_id == principal_id,
        )
        if active_only:
            stmt = stmt.where(RoleAssignmentModel.revoked_at.is_(None))
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_active_for_scope(self, principal_type: str, principal_id: str, scope_type: str, scope_id: str) -> RoleAssignmentModel | None:
        stmt = select(RoleAssignmentModel).where(
            RoleAssignmentModel.principal_type == principal_type, RoleAssignmentModel.principal_id == principal_id,
            RoleAssignmentModel.scope_type == scope_type, RoleAssignmentModel.scope_id == scope_id,
            RoleAssignmentModel.revoked_at.is_(None),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_role(self, role_id: str) -> list[RoleAssignmentModel]:
        stmt = select(RoleAssignmentModel).where(RoleAssignmentModel.role_id == role_id, RoleAssignmentModel.revoked_at.is_(None))
        return list((await self.session.execute(stmt)).scalars().all())


class PermissionRepository(SQLAlchemyRepository[PermissionModel]):
    model = PermissionModel

    async def get_by_key(self, key: str) -> PermissionModel | None:
        stmt = select(PermissionModel).where(PermissionModel.key == key)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_by_resource_type(self, resource_type: str) -> list[PermissionModel]:
        stmt = select(PermissionModel).where(PermissionModel.resource_type == resource_type)
        return list((await self.session.execute(stmt)).scalars().all())
