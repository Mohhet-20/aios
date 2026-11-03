"""RBAC: role assignments across the five contributor roles the
platform settings declare (viewer < contributor < editor < owner <
admin), each optionally scoped to a single doc space or page rather
than tenant-wide. `assign_role` is deliberately last-write-wins (no
commit-spanning lock) — unlike the get-or-create races this platform
guards elsewhere, re-assigning a role is an idempotent overwrite with
no "duplicate row" failure mode to protect against."""
from __future__ import annotations

from docs_platform.config.settings import Settings
from docs_platform.core.exceptions import ValidationError
from docs_platform.models.security import RoleAssignmentModel
from docs_platform.repositories.registry import RepositoryRegistry


class RoleAssignmentService:
    def __init__(self, repos: RepositoryRegistry, settings: Settings):
        self.repos = repos
        self.settings = settings

    def _rank(self, role: str) -> int:
        try:
            return self.settings.contributor_roles.index(role)
        except ValueError:
            raise ValidationError(f"Unsupported role: {role!r}") from None

    async def assign_role(self, tenant_id: str, *, user_id: str, role: str, scope_ref: str | None = None) -> RoleAssignmentModel:
        self._rank(role)  # validates
        existing = await self.repos.role_assignments.get_for_user(tenant_id, user_id, scope_ref=scope_ref)
        if existing is not None:
            existing.role = role
            return await self.repos.role_assignments.update(existing)
        assignment = RoleAssignmentModel(tenant_id=tenant_id, user_id=user_id, role=role, scope_ref=scope_ref)
        return await self.repos.role_assignments.add(assignment)

    async def get_role(self, tenant_id: str, user_id: str, *, scope_ref: str | None = None) -> str | None:
        assignment = await self.repos.role_assignments.get_for_user(tenant_id, user_id, scope_ref=scope_ref)
        if assignment is None and scope_ref is not None:
            # Fall back to a tenant-wide (unscoped) assignment when no
            # scope-specific one exists — a tenant admin shouldn't need
            # a separate row per doc space to have access everywhere.
            assignment = await self.repos.role_assignments.get_for_user(tenant_id, user_id, scope_ref=None)
        return assignment.role if assignment else None

    async def has_at_least(self, tenant_id: str, user_id: str, required_role: str, *, scope_ref: str | None = None) -> bool:
        required_rank = self._rank(required_role)
        role = await self.get_role(tenant_id, user_id, scope_ref=scope_ref)
        if role is None:
            return False
        return self._rank(role) >= required_rank

    async def list_for_user(self, tenant_id: str, user_id: str) -> list[RoleAssignmentModel]:
        return await self.repos.role_assignments.list_for_user(tenant_id, user_id)
