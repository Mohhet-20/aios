"""RBACService — role grants scoped to a resource (workspace or
knowledge_base today; any `resource_type` string works), with
resource-specific grants taking precedence over a broader workspace-wide
grant for the same principal (the same grant-precedence pattern the
Prompt Platform's governance layer uses: more specific wins). An
implicit OWNER role applies to a resource's own `owner_id` field where
the caller supplies one, mirroring a prompt's implicit-owner rule.
"""
from __future__ import annotations

from memory_platform.core.exceptions import AuthorizationError
from memory_platform.database.base import new_uuid
from memory_platform.domain.enums import Permission, Role, permissions_for_role
from memory_platform.models.governance import PermissionGrantModel
from memory_platform.repositories.registry import RepositoryRegistry


class RBACService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def grant_role(self, *, principal_id: str, resource_type: str, resource_id: str, role: Role | str, granted_by: str, principal_type: str = "user") -> PermissionGrantModel:
        role_value = role.value if isinstance(role, Role) else role
        return await self.repos.permission_grants.add(PermissionGrantModel(
            id=new_uuid(), principal_id=principal_id, principal_type=principal_type, resource_type=resource_type,
            resource_id=resource_id, role=role_value, granted_by=granted_by,
        ))

    async def revoke_role(self, grant_id: str) -> None:
        grant = await self.repos.permission_grants.get_or_404(grant_id)
        await self.repos.permission_grants.delete(grant, hard=True)

    async def list_grants_for_principal(self, principal_id: str) -> list[PermissionGrantModel]:
        return await self.repos.permission_grants.list_for_principal(principal_id)

    async def list_grants_for_resource(self, resource_type: str, resource_id: str) -> list[PermissionGrantModel]:
        return await self.repos.permission_grants.list_for_resource(resource_type, resource_id)

    async def resolve_role(
        self, *, principal_id: str, workspace_id: str, resource_type: str | None = None, resource_id: str | None = None, owner_id: str | None = None,
    ) -> Role | None:
        """Resolution order: (1) implicit OWNER if `principal_id == owner_id`,
        (2) a grant on the specific resource, (3) a grant on the workspace
        as a whole. Returns None if nothing applies."""
        if owner_id is not None and principal_id == owner_id:
            return Role.OWNER

        if resource_type is not None and resource_id is not None and resource_type != "workspace":
            specific = [g for g in await self.repos.permission_grants.list_for_resource(resource_type, resource_id) if g.principal_id == principal_id]
            if specific:
                return _highest_role(specific)

        workspace_grants = [g for g in await self.repos.permission_grants.list_for_resource("workspace", workspace_id) if g.principal_id == principal_id]
        if workspace_grants:
            return _highest_role(workspace_grants)
        return None

    async def has_permission(
        self, *, principal_id: str, workspace_id: str, permission: Permission, resource_type: str | None = None, resource_id: str | None = None, owner_id: str | None = None,
    ) -> bool:
        role = await self.resolve_role(principal_id=principal_id, workspace_id=workspace_id, resource_type=resource_type, resource_id=resource_id, owner_id=owner_id)
        if role is None:
            return False
        return permission in permissions_for_role(role)

    async def require_permission(self, *, principal_id: str, workspace_id: str, permission: Permission, resource_type: str | None = None, resource_id: str | None = None, owner_id: str | None = None) -> None:
        if not await self.has_permission(principal_id=principal_id, workspace_id=workspace_id, permission=permission, resource_type=resource_type, resource_id=resource_id, owner_id=owner_id):
            raise AuthorizationError(f"principal '{principal_id}' lacks permission '{permission.value}'" + (f" on {resource_type}:{resource_id}" if resource_type else f" in workspace '{workspace_id}'"))


_ROLE_RANK = {Role.VIEWER: 0, Role.OPERATOR: 1, Role.ADMIN: 2, Role.OWNER: 3}


def _highest_role(grants: list[PermissionGrantModel]) -> Role:
    return max((Role(g.role) for g in grants), key=lambda r: _ROLE_RANK[r])
