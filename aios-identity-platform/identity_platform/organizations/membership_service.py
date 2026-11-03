"""MembershipService: org membership (seat-quota-enforced, guarded by
the `OrganizationMembership` domain entity's transitions) plus the
simpler workspace/team/project membership rows, which have no status
lifecycle of their own — they exist or they don't."""
from __future__ import annotations

from identity_platform.core.exceptions import ConflictError, MembershipError, QuotaExceededError
from identity_platform.domain.enums import MembershipStatus
from identity_platform.models.membership import (
    OrganizationMembershipModel,
    ProjectMembershipModel,
    TeamMembershipModel,
    WorkspaceMembershipModel,
)
from identity_platform.organizations.mappers import apply_org_membership_domain_to_model, org_membership_to_domain
from identity_platform.repositories.registry import RepositoryRegistry


class MembershipService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    # -- organization ------------------------------------------------------

    async def add_organization_member(self, org_id: str, user_id: str, *, invited_by: str | None = None) -> OrganizationMembershipModel:
        await self.repos.organizations.get_or_404(org_id)
        existing = await self.repos.organization_memberships.get_for_org_and_user(org_id, user_id)
        if existing is not None and existing.status != MembershipStatus.REMOVED.value:
            raise ConflictError(f"user '{user_id}' is already a member of organization '{org_id}'")

        # A plain "count active members, compare to seat_quota, then
        # insert" is a check-then-act race under real concurrency (two
        # requests can both read the same under-quota count before
        # either commits its insert) — proven by
        # `tests/performance/test_concurrency.py`, which oversold a
        # 4-seat quota to 11 members under real parallel writers with
        # the naive version of this method. `add_if_under_seat_quota`
        # does the count-and-insert as one atomic SQL statement instead.
        membership = await self.repos.organization_memberships.add_if_under_seat_quota(org_id, user_id, invited_by=invited_by)
        if membership is None:
            org = await self.repos.organizations.get_or_404(org_id)
            raise QuotaExceededError(f"organization '{org_id}' has reached its seat quota ({org.seat_quota})")
        return membership

    async def remove_organization_member(self, org_id: str, user_id: str) -> OrganizationMembershipModel:
        membership = await self.repos.organization_memberships.get_for_org_and_user(org_id, user_id)
        if membership is None:
            raise MembershipError(f"user '{user_id}' is not a member of organization '{org_id}'")
        entity = org_membership_to_domain(membership)
        entity.remove()
        apply_org_membership_domain_to_model(entity, membership)
        return await self.repos.organization_memberships.update(membership)

    async def list_organization_members(self, org_id: str) -> list[OrganizationMembershipModel]:
        return await self.repos.organization_memberships.list_for_organization(org_id)

    # -- workspace -----------------------------------------------------------

    async def add_workspace_member(self, workspace_id: str, user_id: str) -> WorkspaceMembershipModel:
        await self.repos.workspaces.get_or_404(workspace_id)
        existing = await self.repos.workspace_memberships.get_for_workspace_and_user(workspace_id, user_id)
        if existing is not None:
            raise ConflictError(f"user '{user_id}' is already a member of workspace '{workspace_id}'")
        return await self.repos.workspace_memberships.add(WorkspaceMembershipModel(workspace_id=workspace_id, user_id=user_id))

    async def remove_workspace_member(self, workspace_id: str, user_id: str) -> None:
        membership = await self.repos.workspace_memberships.get_for_workspace_and_user(workspace_id, user_id)
        if membership is not None:
            await self.repos.workspace_memberships.delete(membership, hard=True)

    async def list_workspace_members(self, workspace_id: str) -> list[WorkspaceMembershipModel]:
        return await self.repos.workspace_memberships.list_for_workspace(workspace_id)

    # -- team ------------------------------------------------------------------

    async def add_team_member(self, team_id: str, user_id: str) -> TeamMembershipModel:
        await self.repos.teams.get_or_404(team_id)
        existing = [m for m in await self.repos.team_memberships.list_for_team(team_id) if m.user_id == user_id]
        if existing:
            raise ConflictError(f"user '{user_id}' is already a member of team '{team_id}'")
        return await self.repos.team_memberships.add(TeamMembershipModel(team_id=team_id, user_id=user_id))

    async def remove_team_member(self, team_id: str, user_id: str) -> None:
        for membership in await self.repos.team_memberships.list_for_team(team_id):
            if membership.user_id == user_id:
                await self.repos.team_memberships.delete(membership, hard=True)
                return

    async def list_team_members(self, team_id: str) -> list[TeamMembershipModel]:
        return await self.repos.team_memberships.list_for_team(team_id)

    # -- project -----------------------------------------------------------------

    async def add_project_member(self, project_id: str, user_id: str) -> ProjectMembershipModel:
        await self.repos.projects.get_or_404(project_id)
        existing = [m for m in await self.repos.project_memberships.list_for_project(project_id) if m.user_id == user_id]
        if existing:
            raise ConflictError(f"user '{user_id}' is already a member of project '{project_id}'")
        return await self.repos.project_memberships.add(ProjectMembershipModel(project_id=project_id, user_id=user_id))

    async def remove_project_member(self, project_id: str, user_id: str) -> None:
        for membership in await self.repos.project_memberships.list_for_project(project_id):
            if membership.user_id == user_id:
                await self.repos.project_memberships.delete(membership, hard=True)
                return

    async def list_project_members(self, project_id: str) -> list[ProjectMembershipModel]:
        return await self.repos.project_memberships.list_for_project(project_id)
