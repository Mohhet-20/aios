from __future__ import annotations

from sqlalchemy import select

from identity_platform.models.team import TeamModel
from identity_platform.repositories.base import SQLAlchemyRepository


class TeamRepository(SQLAlchemyRepository[TeamModel]):
    model = TeamModel

    async def list_for_organization(self, organization_id: str) -> list[TeamModel]:
        stmt = select(TeamModel).where(TeamModel.organization_id == organization_id)
        return list((await self.session.execute(stmt)).scalars().all())
