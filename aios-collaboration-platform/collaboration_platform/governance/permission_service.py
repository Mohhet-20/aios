"""PermissionService: resolves "what access level does this principal
have" across three tiers, most specific wins:
1. `AssetPermissionModel` — an explicit per-asset override (narrower
   or wider than the workspace default for this one asset).
2. `WorkspacePermissionModel` — an explicit grant to a principal
   (user or *team*) that doesn't require formal workspace membership,
   e.g. "this team can comment on everything in this workspace"
   without adding every team member to the roster.
3. `WorkspaceMemberModel` — plain membership, the common case.

If none of the three has a row for this principal, the principal has
no access. This is deliberately a small ordered role system (see
`WorkspaceRole`), not the Identity Platform's fine-grained
`resource_type:action` grammar — that engine already exists one layer
down for platform-wide RBAC; this only needs to answer
workspace/asset-scoped view/comment/edit/admin questions."""
from __future__ import annotations

from collaboration_platform.core.exceptions import PermissionDeniedError
from collaboration_platform.domain.enums import PrincipalType, WorkspaceRole
from collaboration_platform.models.governance import AssetPermissionModel, WorkspacePermissionModel
from collaboration_platform.repositories.registry import RepositoryRegistry
from collaboration_platform.workspace.member_service import role_at_least


class PermissionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def effective_role(self, asset_id: str, principal_id: str, *, principal_type: PrincipalType = PrincipalType.USER) -> WorkspaceRole | None:
        asset = await self.repos.assets.get_or_404(asset_id)

        asset_override = await self.repos.asset_permissions.get_for_principal(asset_id, principal_type.value, principal_id)
        if asset_override is not None:
            return WorkspaceRole(asset_override.role)

        workspace_grant = await self.repos.workspace_permissions.get_for_principal(asset.workspace_id, principal_type.value, principal_id)
        if workspace_grant is not None:
            return WorkspaceRole(workspace_grant.role)

        if principal_type == PrincipalType.USER:
            member = await self.repos.workspace_members.get_for_workspace_and_user(asset.workspace_id, principal_id)
            if member is not None:
                return WorkspaceRole(member.role)

        return None

    async def require_role(self, asset_id: str, principal_id: str, *, minimum: WorkspaceRole, principal_type: PrincipalType = PrincipalType.USER) -> WorkspaceRole:
        role = await self.effective_role(asset_id, principal_id, principal_type=principal_type)
        if role is None or not role_at_least(role, minimum):
            raise PermissionDeniedError(f"principal '{principal_id}' does not have at least '{minimum.value}' access to asset '{asset_id}'")
        return role

    async def grant_workspace_permission(
        self, workspace_id: str, principal_type: PrincipalType, principal_id: str, role: WorkspaceRole, *, granted_by: str | None = None
    ) -> WorkspacePermissionModel:
        await self.repos.workspaces.get_or_404(workspace_id)
        existing = await self.repos.workspace_permissions.get_for_principal(workspace_id, principal_type.value, principal_id)
        if existing is not None:
            existing.role = role.value
            existing.granted_by = granted_by
            return await self.repos.workspace_permissions.update(existing)
        return await self.repos.workspace_permissions.add(WorkspacePermissionModel(
            workspace_id=workspace_id, principal_type=principal_type.value, principal_id=principal_id, role=role.value, granted_by=granted_by,
        ))

    async def grant_asset_permission(
        self, asset_id: str, principal_type: PrincipalType, principal_id: str, role: WorkspaceRole, *, granted_by: str | None = None
    ) -> AssetPermissionModel:
        await self.repos.assets.get_or_404(asset_id)
        existing = await self.repos.asset_permissions.get_for_principal(asset_id, principal_type.value, principal_id)
        if existing is not None:
            existing.role = role.value
            existing.granted_by = granted_by
            return await self.repos.asset_permissions.update(existing)
        return await self.repos.asset_permissions.add(AssetPermissionModel(
            asset_id=asset_id, principal_type=principal_type.value, principal_id=principal_id, role=role.value, granted_by=granted_by,
        ))
