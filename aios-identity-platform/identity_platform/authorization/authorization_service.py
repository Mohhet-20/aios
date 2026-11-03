"""AuthorizationService: the policy decision point. `has_permission`
resolves every active role assignment a principal holds — both at the
requested scope and, since a system-scoped grant (e.g. `system_admin`)
applies everywhere, at the system scope — and checks whether any
granted role's permission list covers the requested key via an exact
match, a `"<resource_type>:manage"` blanket grant, or the `"*"`
super-admin wildcard. This is intentionally the single place that
walks that precedence, so every caller (REST middleware, service-layer
checks) gets identical behavior."""
from __future__ import annotations

from identity_platform.authorization.registry import WILDCARD_ALL
from identity_platform.core.exceptions import PermissionDeniedError
from identity_platform.domain.enums import RoleScopeType
from identity_platform.models.rbac import RoleAssignmentModel
from identity_platform.repositories.registry import RepositoryRegistry

_SYSTEM_SCOPE_ID = "system"


def _role_grants(permissions: list[str], permission_key: str) -> bool:
    if WILDCARD_ALL in permissions or permission_key in permissions:
        return True
    resource_type = permission_key.split(":", 1)[0]
    return f"{resource_type}:manage" in permissions


class AuthorizationService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def _active_assignments(self, principal_type: str, principal_id: str, scope_type: RoleScopeType, scope_id: str) -> list[RoleAssignmentModel]:
        assignments = list(await self.repos.role_assignments.list_for_principal(principal_type, principal_id))
        return [
            a for a in assignments
            if (a.scope_type == scope_type.value and a.scope_id == scope_id) or a.scope_type == RoleScopeType.SYSTEM.value
        ]

    async def has_permission(
        self, *, principal_type: str, principal_id: str, permission_key: str, scope_type: RoleScopeType, scope_id: str,
    ) -> bool:
        assignments = await self._active_assignments(principal_type, principal_id, scope_type, scope_id)
        roles = await self.repos.roles.get_many([a.role_id for a in assignments])
        return any(_role_grants(role.permissions, permission_key) for role in roles)

    async def require_permission(
        self, *, principal_type: str, principal_id: str, permission_key: str, scope_type: RoleScopeType, scope_id: str,
    ) -> None:
        allowed = await self.has_permission(
            principal_type=principal_type, principal_id=principal_id, permission_key=permission_key,
            scope_type=scope_type, scope_id=scope_id,
        )
        if not allowed:
            raise PermissionDeniedError(
                f"{principal_type} '{principal_id}' lacks permission '{permission_key}' at {scope_type.value} '{scope_id}'"
            )

    async def effective_permissions(self, *, principal_type: str, principal_id: str, scope_type: RoleScopeType, scope_id: str) -> set[str]:
        """Union of every permission key granted by every role the
        principal holds at this scope (wildcard/manage grants are
        expanded isn't attempted here — callers checking a specific key
        should use `has_permission`; this is for display purposes)."""
        assignments = await self._active_assignments(principal_type, principal_id, scope_type, scope_id)
        roles = await self.repos.roles.get_many([a.role_id for a in assignments])
        keys: set[str] = set()
        for role in roles:
            keys.update(role.permissions)
        return keys
