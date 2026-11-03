from app.models.organization import (
    OrganizationMembershipModel,
    OrganizationModel,
    TeamMembershipModel,
    TeamModel,
)
from app.repositories.base import SQLAlchemyRepository


class OrganizationRepository(SQLAlchemyRepository[OrganizationModel]):
    model = OrganizationModel


class OrganizationMembershipRepository(SQLAlchemyRepository[OrganizationMembershipModel]):
    model = OrganizationMembershipModel

    async def get_membership(self, organization_id: str, user_id: str) -> OrganizationMembershipModel | None:
        results = await self.list(organization_id=organization_id, user_id=user_id)
        return results[0] if results else None


class TeamRepository(SQLAlchemyRepository[TeamModel]):
    model = TeamModel


class TeamMembershipRepository(SQLAlchemyRepository[TeamMembershipModel]):
    model = TeamMembershipModel
