"""OrganizationService and TeamService: organization membership + team
grouping. Membership is the resource that RBAC checks ultimately hang off
(a user's `role` claim in their JWT is derived from their
`OrganizationMembershipModel.role` at login time)."""

from __future__ import annotations

from app.application.services.base_service import BaseCRUDService
from app.core.exceptions import ConflictError
from app.models.organization import (
    OrganizationMembershipModel,
    OrganizationModel,
    TeamMembershipModel,
    TeamModel,
)
from app.repositories.organization_repository import (
    OrganizationMembershipRepository,
    OrganizationRepository,
    TeamMembershipRepository,
    TeamRepository,
)


class OrganizationService(BaseCRUDService[OrganizationModel]):
    def __init__(self, repository: OrganizationRepository, memberships: OrganizationMembershipRepository):
        super().__init__(repository)
        self.memberships = memberships

    async def add_member(
        self, organization_id: str, user_id: str, role: str = "member"
    ) -> OrganizationMembershipModel:
        existing = await self.memberships.get_membership(organization_id, user_id)
        if existing:
            raise ConflictError("User is already a member of this organization")
        membership = OrganizationMembershipModel(organization_id=organization_id, user_id=user_id, role=role)
        return await self.memberships.add(membership)

    async def list_members(self, organization_id: str) -> list[OrganizationMembershipModel]:
        return await self.memberships.list(organization_id=organization_id)


class TeamService(BaseCRUDService[TeamModel]):
    def __init__(self, repository: TeamRepository, memberships: TeamMembershipRepository):
        super().__init__(repository)
        self.memberships = memberships

    async def add_member(self, team_id: str, user_id: str) -> TeamMembershipModel:
        membership = TeamMembershipModel(team_id=team_id, user_id=user_id)
        return await self.memberships.add(membership)

    async def list_members(self, team_id: str) -> list[TeamMembershipModel]:
        return await self.memberships.list(team_id=team_id)
