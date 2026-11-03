"""WorkspaceMemberService: add/remove/update workspace members and
answer "does principal X have at least role Y" access checks. Roles
are ordered (`WorkspaceRole`, viewer < commenter < editor < admin <
owner) so "at least" comparisons are a simple index comparison rather
than an explicit adjacency table."""
from __future__ import annotations

from collaboration_platform.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from collaboration_platform.domain.enums import WorkspaceRole
from collaboration_platform.models.workspace import WorkspaceMemberModel
from collaboration_platform.repositories.registry import RepositoryRegistry

_ROLE_ORDER = [WorkspaceRole.VIEWER, WorkspaceRole.COMMENTER, WorkspaceRole.EDITOR, WorkspaceRole.ADMIN, WorkspaceRole.OWNER]


def role_at_least(role: WorkspaceRole, minimum: WorkspaceRole) -> bool:
    return _ROLE_ORDER.index(role) >= _ROLE_ORDER.index(minimum)


class WorkspaceMemberService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def add_member(self, workspace_id: str, user_id: str, *, role: WorkspaceRole = WorkspaceRole.VIEWER, invited_by: str | None = None) -> WorkspaceMemberModel:
        await self.repos.workspaces.get_or_404(workspace_id)
        existing = await self.repos.workspace_members.get_for_workspace_and_user(workspace_id, user_id)
        if existing is not None:
            raise ConflictError(f"user '{user_id}' is already a member of workspace '{workspace_id}'")
        return await self.repos.workspace_members.add(
            WorkspaceMemberModel(workspace_id=workspace_id, user_id=user_id, role=role.value, invited_by=invited_by)
        )

    async def update_role(self, workspace_id: str, user_id: str, *, role: WorkspaceRole) -> WorkspaceMemberModel:
        member = await self.repos.workspace_members.get_for_workspace_and_user(workspace_id, user_id)
        if member is None:
            raise NotFoundError(f"user '{user_id}' is not a member of workspace '{workspace_id}'")
        member.role = role.value
        return await self.repos.workspace_members.update(member)

    async def remove_member(self, workspace_id: str, user_id: str) -> None:
        member = await self.repos.workspace_members.get_for_workspace_and_user(workspace_id, user_id)
        if member is None:
            raise NotFoundError(f"user '{user_id}' is not a member of workspace '{workspace_id}'")
        await self.repos.workspace_members.delete(member, hard=True)

    async def list_members(self, workspace_id: str) -> list[WorkspaceMemberModel]:
        return await self.repos.workspace_members.list_for_workspace(workspace_id)

    async def get_role(self, workspace_id: str, user_id: str) -> WorkspaceRole | None:
        member = await self.repos.workspace_members.get_for_workspace_and_user(workspace_id, user_id)
        return WorkspaceRole(member.role) if member else None

    async def require_role(self, workspace_id: str, user_id: str, *, minimum: WorkspaceRole) -> WorkspaceRole:
        role = await self.get_role(workspace_id, user_id)
        if role is None or not role_at_least(role, minimum):
            raise PermissionDeniedError(
                f"user '{user_id}' does not have at least '{minimum.value}' access to workspace '{workspace_id}'"
            )
        return role
