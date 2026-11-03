"""RBACService: grants, revocations, and permission checks over
`PermissionGrantModel` — the `Role`/`Permission`/`ROLE_PERMISSIONS` table
in `domain/enums.py` is the fixed policy ("what can an OPERATOR do");
this service is the assignment layer ("who is an OPERATOR on what").

A grant's `resource_type` is `workspace` or `workflow`. Effective-
permission resolution checks the more specific resource first: a
workflow-level grant beats a workspace-level grant for that same
workflow, so "give this one person OPERATOR on just this one workflow,
without touching their access to anything else in the workspace" is a
real, first-class thing this platform can express — not just
workspace-wide all-or-nothing RBAC."""
from __future__ import annotations

from workflow_platform.core.exceptions import AuthorizationError
from workflow_platform.domain.enums import Permission, Role, permissions_for_role
from workflow_platform.models.governance import AuditLogEntryModel, PermissionGrantModel
from workflow_platform.repositories.registry import RepositoryRegistry


class RBACService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def grant(
        self, principal_id: str, resource_type: str, resource_id: str, role: Role | str, *, granted_by: str,
        principal_type: str = "user",
    ) -> PermissionGrantModel:
        role = Role(role).value
        grant = await self.repos.permission_grants.add(PermissionGrantModel(
            principal_id=principal_id, principal_type=principal_type, resource_type=resource_type,
            resource_id=resource_id, role=role, granted_by=granted_by,
        ))
        await self.repos.audit_log.add(AuditLogEntryModel(
            actor_id=granted_by, action="rbac_grant", resource_type=resource_type, resource_id=resource_id,
            before=None, after={"principal_id": principal_id, "role": role},
        ))
        return grant

    async def revoke(self, grant_id: str, *, revoked_by: str) -> None:
        grant = await self.repos.permission_grants.get_or_404(grant_id)
        await self.repos.permission_grants.delete(grant, hard=True)
        await self.repos.audit_log.add(AuditLogEntryModel(
            actor_id=revoked_by, action="rbac_revoke", resource_type=grant.resource_type, resource_id=grant.resource_id,
            before={"principal_id": grant.principal_id, "role": grant.role}, after=None,
        ))

    async def list_grants_for_principal(self, principal_id: str) -> list[PermissionGrantModel]:
        return await self.repos.permission_grants.list_for_principal(principal_id)

    async def list_grants_for_resource(self, resource_type: str, resource_id: str) -> list[PermissionGrantModel]:
        return await self.repos.permission_grants.list_for_resource(resource_type, resource_id)

    async def get_effective_role(self, principal_id: str, *, workspace_id: str, workflow_id: str | None = None) -> Role | None:
        if workflow_id is not None:
            grant = await self.repos.permission_grants.get_for_resource(principal_id, "workflow", workflow_id)
            if grant is not None:
                return Role(grant.role)
        grant = await self.repos.permission_grants.get_for_resource(principal_id, "workspace", workspace_id)
        return Role(grant.role) if grant is not None else None

    async def get_effective_permissions(self, principal_id: str, *, workspace_id: str, workflow_id: str | None = None) -> frozenset[Permission]:
        role = await self.get_effective_role(principal_id, workspace_id=workspace_id, workflow_id=workflow_id)
        return permissions_for_role(role) if role is not None else frozenset()

    async def has_permission(self, principal_id: str, permission: Permission, *, workspace_id: str, workflow_id: str | None = None) -> bool:
        permissions = await self.get_effective_permissions(principal_id, workspace_id=workspace_id, workflow_id=workflow_id)
        return permission in permissions

    async def require_permission(self, principal_id: str, permission: Permission, *, workspace_id: str, workflow_id: str | None = None) -> None:
        if not await self.has_permission(principal_id, permission, workspace_id=workspace_id, workflow_id=workflow_id):
            scope = f"workflow '{workflow_id}'" if workflow_id else f"workspace '{workspace_id}'"
            raise AuthorizationError(f"principal '{principal_id}' lacks '{permission.value}' on {scope}")
