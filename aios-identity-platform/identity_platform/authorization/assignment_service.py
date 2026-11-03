"""RoleAssignmentService: binds a principal (user/service_account/group)
to a role at a specific scope instance (e.g. this workspace, that
project). Revocation is soft (`revoked_at` set) rather than a delete,
so "who had access to X on date Y" stays answerable for audit."""
from __future__ import annotations

from identity_platform.core.exceptions import RoleError
from identity_platform.database.base import utcnow
from identity_platform.domain.enums import RoleScopeType
from identity_platform.models.rbac import RoleAssignmentModel
from identity_platform.repositories.registry import RepositoryRegistry


class RoleAssignmentService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def assign_role(
        self, *, principal_type: str, principal_id: str, role_id: str, scope_type: RoleScopeType,
        scope_id: str, granted_by: str,
    ) -> RoleAssignmentModel:
        role = await self.repos.roles.get_or_404(role_id)
        if role.scope_type != scope_type.value:
            raise RoleError(f"role '{role_id}' is scoped to '{role.scope_type}', cannot assign at '{scope_type.value}' scope")

        existing = await self.repos.role_assignments.get_active_for_scope(principal_type, principal_id, scope_type.value, scope_id)
        if existing is not None and existing.role_id == role_id:
            return existing

        return await self.repos.role_assignments.add(RoleAssignmentModel(
            principal_type=principal_type, principal_id=principal_id, role_id=role_id,
            scope_type=scope_type.value, scope_id=scope_id, granted_by=granted_by,
        ))

    async def revoke_assignment(self, assignment_id: str) -> RoleAssignmentModel:
        assignment = await self.repos.role_assignments.get_or_404(assignment_id)
        assignment.revoked_at = utcnow()
        return await self.repos.role_assignments.update(assignment)

    async def list_for_principal(self, principal_type: str, principal_id: str) -> list[RoleAssignmentModel]:
        return await self.repos.role_assignments.list_for_principal(principal_type, principal_id)
