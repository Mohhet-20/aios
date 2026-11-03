"""RoleService: CRUD for custom, organization-scoped roles. Built-in
system roles (`organization_id is None`) are read-only here — they are
only ever written by `bootstrap.py`'s seed; attempting to mutate one
through this service raises `RoleError`."""
from __future__ import annotations

from identity_platform.core.exceptions import ConflictError, RoleError, UnknownPermissionError
from identity_platform.authorization.registry import PERMISSION_KEYS, WILDCARD_ALL
from identity_platform.domain.enums import RoleScopeType
from identity_platform.models.rbac import RoleModel
from identity_platform.repositories.registry import RepositoryRegistry


def _validate_permissions(permissions: list[str]) -> None:
    for key in permissions:
        if key == WILDCARD_ALL or key.endswith(":manage"):
            continue
        if key not in PERMISSION_KEYS:
            raise UnknownPermissionError(f"'{key}' is not a registered permission")


class RoleService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_custom_role(
        self, organization_id: str, *, name: str, slug: str, scope_type: RoleScopeType,
        permissions: list[str], description: str | None = None,
    ) -> RoleModel:
        existing = await self.repos.roles.get_by_slug(organization_id, slug)
        if existing is not None:
            raise ConflictError(f"role slug '{slug}' already exists for this organization")
        _validate_permissions(permissions)

        role = RoleModel(
            organization_id=organization_id, scope_type=scope_type.value, name=name, slug=slug,
            description=description, is_custom=True, permissions=list(permissions),
        )
        return await self.repos.roles.add(role)

    async def update_permissions(self, role_id: str, permissions: list[str]) -> RoleModel:
        role = await self.repos.roles.get_or_404(role_id)
        if not role.is_custom:
            raise RoleError("built-in system roles cannot be modified")
        _validate_permissions(permissions)
        role.permissions = list(permissions)
        return await self.repos.roles.update(role)

    async def delete_custom_role(self, role_id: str) -> None:
        role = await self.repos.roles.get_or_404(role_id)
        if not role.is_custom:
            raise RoleError("built-in system roles cannot be deleted")
        active_assignments = await self.repos.role_assignments.list_for_role(role_id)
        if active_assignments:
            raise ConflictError(f"role '{role_id}' still has {len(active_assignments)} active assignment(s)")
        await self.repos.roles.delete(role, hard=True)

    async def list_available_for_organization(self, organization_id: str) -> list[RoleModel]:
        return await self.repos.roles.list_available_for_organization(organization_id)
