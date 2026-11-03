"""Lightweight RBAC: role grants scoped per (tenant, principal,
optional scope) across the four role levels the prompt specifies
(viewer, analyst, editor, admin), plus a real hierarchy-aware
permission check other services (row/column-level security,
dashboards, reports) can call rather than re-implementing "is this
role high enough" logic themselves."""
from __future__ import annotations

from analytics_platform.core.exceptions import ValidationError
from analytics_platform.domain.enums import SecurityRoleLevel
from analytics_platform.models.security import AnalyticsRoleGrantModel
from analytics_platform.repositories.registry import RepositoryRegistry

# Ordered lowest -> highest. Index comparison is the entire hierarchy check.
ROLE_ORDER: list[str] = [
    SecurityRoleLevel.VIEWER.value,
    SecurityRoleLevel.ANALYST.value,
    SecurityRoleLevel.EDITOR.value,
    SecurityRoleLevel.ADMIN.value,
]


def role_satisfies(actual_role: str, required_role: str) -> bool:
    """True if `actual_role` is at or above `required_role` in the
    hierarchy. Unknown role strings never satisfy anything -- they
    fail closed rather than raising, since this is meant to sit
    directly in an access-check hot path."""
    if actual_role not in ROLE_ORDER or required_role not in ROLE_ORDER:
        return False
    return ROLE_ORDER.index(actual_role) >= ROLE_ORDER.index(required_role)


class AnalyticsRbacService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    def _assert_valid_role(self, role_level: str) -> None:
        if role_level not in {r.value for r in SecurityRoleLevel}:
            raise ValidationError(f"'{role_level}' is not a recognized role level")

    async def grant_role(
        self, tenant_id: str, principal_id: str, *, role_level: str, scope: str | None = None,
    ) -> AnalyticsRoleGrantModel:
        self._assert_valid_role(role_level)
        existing = await self.repos.role_grants.get_for_principal(tenant_id, principal_id, scope=scope)
        if existing is not None:
            existing.role_level = role_level
            return await self.repos.role_grants.update(existing)
        grant = AnalyticsRoleGrantModel(tenant_id=tenant_id, principal_id=principal_id, role_level=role_level, scope=scope)
        return await self.repos.role_grants.add(grant)

    async def get_role(self, tenant_id: str, principal_id: str, *, scope: str | None = None) -> str | None:
        grant = await self.repos.role_grants.get_for_principal(tenant_id, principal_id, scope=scope)
        return grant.role_level if grant is not None else None

    async def list_for_tenant(self, tenant_id: str) -> list[AnalyticsRoleGrantModel]:
        return await self.repos.role_grants.list_for_tenant(tenant_id)

    async def check_permission(self, tenant_id: str, principal_id: str, *, required_role: str, scope: str | None = None) -> bool:
        actual_role = await self.get_role(tenant_id, principal_id, scope=scope)
        if actual_role is None:
            return False
        return role_satisfies(actual_role, required_role)

    async def revoke_role(self, tenant_id: str, principal_id: str, *, scope: str | None = None) -> None:
        grant = await self.repos.role_grants.get_for_principal(tenant_id, principal_id, scope=scope)
        if grant is not None:
            await self.repos.role_grants.delete(grant, hard=True)
