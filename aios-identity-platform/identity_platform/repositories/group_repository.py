from __future__ import annotations

from sqlalchemy import select

from identity_platform.models.group import GroupModel
from identity_platform.repositories.base import SQLAlchemyRepository


class GroupRepository(SQLAlchemyRepository[GroupModel]):
    model = GroupModel

    async def list_for_organization(self, organization_id: str) -> list[GroupModel]:
        stmt = select(GroupModel).where(GroupModel.organization_id == organization_id)
        return list((await self.session.execute(stmt)).scalars().all())
