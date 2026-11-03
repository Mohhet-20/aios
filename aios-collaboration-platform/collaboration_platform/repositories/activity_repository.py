from __future__ import annotations

from sqlalchemy import desc, select

from collaboration_platform.models.activity import ActivityEventModel
from collaboration_platform.repositories.base import SQLAlchemyRepository


class ActivityEventRepository(SQLAlchemyRepository[ActivityEventModel]):
    model = ActivityEventModel

    async def list_for_workspace(self, workspace_id: str, *, limit: int = 100) -> list[ActivityEventModel]:
        stmt = (
            select(ActivityEventModel)
            .where(ActivityEventModel.workspace_id == workspace_id)
            .order_by(desc(ActivityEventModel.created_at))
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_project(self, project_id: str, *, limit: int = 100) -> list[ActivityEventModel]:
        stmt = (
            select(ActivityEventModel)
            .where(ActivityEventModel.project_id == project_id)
            .order_by(desc(ActivityEventModel.created_at))
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_asset(self, asset_id: str, *, limit: int = 100) -> list[ActivityEventModel]:
        stmt = (
            select(ActivityEventModel)
            .where(ActivityEventModel.asset_id == asset_id)
            .order_by(desc(ActivityEventModel.created_at))
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_actor(self, actor_id: str, *, limit: int = 100) -> list[ActivityEventModel]:
        stmt = (
            select(ActivityEventModel)
            .where(ActivityEventModel.actor_id == actor_id)
            .order_by(desc(ActivityEventModel.created_at))
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_organization(self, organization_id: str, *, limit: int = 100) -> list[ActivityEventModel]:
        stmt = (
            select(ActivityEventModel)
            .where(ActivityEventModel.organization_id == organization_id)
            .order_by(desc(ActivityEventModel.created_at))
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())
