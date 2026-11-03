"""RBACService: workspace/resource-scoped role-based access control.
A principal (user or service account) holds at most one *active* role
per resource — granting a new role first revokes any existing active
grant for that exact (principal, resource_type, resource_id) tuple,
rather than accumulating stale grants. `has_permission`/
`require_permission` resolve a principal's effective role for a
resource and check it against the fixed `ROLE_PERMISSIONS` map from
`domain/enums.py`."""
from __future__ import annotations

from eval_platform.core.exceptions import AuthorizationError, ValidationError
from eval_platform.database.base import utcnow
from eval_platform.domain.enums import Permission, Role, permissions_for_role
from eval_platform.models.governance import PermissionGrantModel
from eval_platform.repositories.registry import RepositoryRegistry

_VALID_ROLES = {r.value for r in Role}


class RBACService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def grant_role(
        self, principal_id: str, *, resource_type: str, resource_id: str, role: str, granted_by: str, principal_type: str = "user",
    ) -> PermissionGrantModel:
        if role not in _VALID_ROLES:
            raise ValidationError(f"unknown role '{role}' (must be one of {sorted(_VALID_ROLES)})")

        existing = await self.repos.permission_grants.get_for_resource(principal_id, resource_type, resource_id)
        if existing is not None and existing.revoked_at is None:
            existing.revoked_at = utcnow()
            await self.repos.permission_grants.update(existing)

        return await self.repos.permission_grants.add(PermissionGrantModel(
            principal_id=principal_id, principal_type=principal_type, resource_type=resource_type,
            resource_id=resource_id, role=role, granted_by=granted_by,
        ))

    async def revoke_role(self, principal_id: str, *, resource_type: str, resource_id: str) -> PermissionGrantModel | None:
        existing = await self.repos.permission_grants.get_for_resource(principal_id, resource_type, resource_id)
        if existing is None or existing.revoked_at is not None:
            return None
        existing.revoked_at = utcnow()
        return await self.repos.permission_grants.update(existing)

    async def get_effective_role(self, principal_id: str, *, resource_type: str, resource_id: str) -> Role | None:
        grant = await self.repos.permission_grants.get_for_resource(principal_id, resource_type, resource_id)
        if grant is None or grant.revoked_at is not None:
            return None
        return Role(grant.role)

    async def has_permission(self, principal_id: str, *, resource_type: str, resource_id: str, permission: Permission | str) -> bool:
        role = await self.get_effective_role(principal_id, resource_type=resource_type, resource_id=resource_id)
        if role is None:
            return False
        return Permission(permission) in permissions_for_role(role)

    async def require_permission(self, principal_id: str, *, resource_type: str, resource_id: str, permission: Permission | str) -> None:
        if not await self.has_permission(principal_id, resource_type=resource_type, resource_id=resource_id, permission=permission):
            raise AuthorizationError(
                f"principal '{principal_id}' lacks permission '{Permission(permission).value}' on {resource_type} '{resource_id}'"
            )

    async def list_grants_for_principal(self, principal_id: str) -> list[PermissionGrantModel]:
        return await self.repos.permission_grants.list_for_principal(principal_id)
