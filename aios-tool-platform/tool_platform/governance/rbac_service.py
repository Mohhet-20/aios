"""RBACService: "is this principal allowed to act on this resource at
all" — the authorization question, distinct from PolicyEngine's "even
if allowed, has this principal/agent hit a guardrail right now" and from
sandbox/network-policy's "is this connector allowed to touch this
network/filesystem." Three layers, three separate concerns, on purpose.

A grant is workspace-scoped by convention (`resource_type="workspace"`,
`resource_id=<workspace_id>`) rather than one row per tool — granting a
role per-individual-tool for an org with thousands of registered tools
(the self-review's own stated scale target) would make RBAC administration
itself the bottleneck. A grant can still be issued against a specific
resource (`resource_type="tool"`, `resource_id=<tool_id>`) when a
narrower, tool-specific grant is genuinely what's wanted; `check_permission`
checks the specific-resource grant first, then falls back to the
workspace-wide grant, so both models compose without special-casing."""
from __future__ import annotations

from tool_platform.core.exceptions import AuthorizationError
from tool_platform.domain.enums import Permission, Role, permissions_for_role
from tool_platform.models.governance import PermissionGrantModel
from tool_platform.repositories.registry import RepositoryRegistry
from tool_platform.clock import utc_now


class RBACService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def grant(
        self, principal_id: str, resource_type: str, resource_id: str, role: str, *,
        granted_by: str, principal_type: str = "user",
    ) -> PermissionGrantModel:
        Role(role)  # raises ValueError (caller sees a clean 400 upstream) for an unknown role name
        return await self.repos.permission_grants.add(PermissionGrantModel(
            principal_id=principal_id, principal_type=principal_type, resource_type=resource_type,
            resource_id=resource_id, role=role, granted_by=granted_by,
        ))

    async def revoke(self, grant_id: str) -> PermissionGrantModel:

        grant = await self.repos.permission_grants.get_or_404(grant_id)
        grant.revoked_at = utc_now()
        return await self.repos.permission_grants.update(grant)

    async def list_for_principal(self, principal_id: str) -> list[PermissionGrantModel]:
        return await self.repos.permission_grants.list_for_principal(principal_id)

    async def _active_grants(
        self, principal_id: str, resource_type: str, resource_id: str
    ) -> list[PermissionGrantModel]:
        grant = await self.repos.permission_grants.get_for_resource(principal_id, resource_type, resource_id)
        return [grant] if grant is not None and grant.revoked_at is None else []

    async def has_permission(
        self, principal_id: str, permission: Permission | str, *, resource_type: str, resource_id: str,
        workspace_id: str | None = None,
    ) -> bool:
        """Checks a specific-resource grant first, then the ambient
        workspace-wide grant (if `workspace_id` is given and differs from
        `resource_id`) — either one satisfying the permission is enough."""
        permission = Permission(permission)

        for grant in await self._active_grants(principal_id, resource_type, resource_id):
            if permission in permissions_for_role(grant.role):
                return True

        if workspace_id is not None and not (resource_type == "workspace" and resource_id == workspace_id):
            for grant in await self._active_grants(principal_id, "workspace", workspace_id):
                if permission in permissions_for_role(grant.role):
                    return True

        return False

    async def enforce_permission(
        self, principal_id: str, permission: Permission | str, *, resource_type: str, resource_id: str,
        workspace_id: str | None = None,
    ) -> None:
        allowed = await self.has_permission(
            principal_id, permission, resource_type=resource_type, resource_id=resource_id, workspace_id=workspace_id,
        )
        if not allowed:
            raise AuthorizationError(
                f"principal '{principal_id}' lacks permission '{Permission(permission).value}' on "
                f"{resource_type} '{resource_id}'"
            )

    def enforce_workspace_isolation(self, resource_workspace_id: str, requested_workspace_id: str) -> None:
        """A resource loaded for workspace A must never be operated on in
        the context of a request scoped to workspace B — the same check
        every `list_for_workspace(...)` query implicitly enforces at the
        DB layer, surfaced explicitly for a caller that already has the
        resource in hand (e.g. after a cross-workspace ID guess) and wants
        to fail loudly rather than silently leak across the boundary."""
        if resource_workspace_id != requested_workspace_id:
            raise AuthorizationError(
                f"resource belongs to workspace '{resource_workspace_id}', not '{requested_workspace_id}' "
                "— cross-workspace access is denied"
            )

    def enforce_organization_isolation(self, resource_org_id: str, requested_org_id: str) -> None:
        if resource_org_id != requested_org_id:
            raise AuthorizationError(
                f"resource belongs to organization '{resource_org_id}', not '{requested_org_id}' "
                "— cross-organization access is denied"
            )
