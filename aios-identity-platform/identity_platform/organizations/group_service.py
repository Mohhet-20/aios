"""GroupService: lightweight org-scoped principal for bundling role
grants; membership add/remove lives here rather than in
`membership_service.py` since a group has no status lifecycle of its
own (unlike org/workspace/team/project membership rows)."""
from __future__ import annotations

from identity_platform.core.exceptions import ConflictError
from identity_platform.models.group import GroupModel
from identity_platform.models.membership import GroupMembershipModel
from identity_platform.repositories.registry import RepositoryRegistry


class GroupService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_group(self, org_id: str, *, name: str, description: str | None = None) -> GroupModel:
        await self.repos.organizations.get_or_404(org_id)
        return await self.repos.groups.add(GroupModel(organization_id=org_id, name=name, description=description))

    async def add_member(self, group_id: str, user_id: str) -> GroupMembershipModel:
        await self.repos.groups.get_or_404(group_id)
        existing = [m for m in await self.repos.group_memberships.list_for_group(group_id) if m.user_id == user_id]
        if existing:
            raise ConflictError(f"user '{user_id}' is already a member of group '{group_id}'")
        return await self.repos.group_memberships.add(GroupMembershipModel(group_id=group_id, user_id=user_id))

    async def remove_member(self, group_id: str, user_id: str) -> None:
        for membership in await self.repos.group_memberships.list_for_group(group_id):
            if membership.user_id == user_id:
                await self.repos.group_memberships.delete(membership, hard=True)
                return

    async def list_members(self, group_id: str) -> list[GroupMembershipModel]:
        return await self.repos.group_memberships.list_for_group(group_id)

    async def list_for_organization(self, org_id: str) -> list[GroupModel]:
        return await self.repos.groups.list_for_organization(org_id)
