from __future__ import annotations

from sqlalchemy import select

from tool_platform.models.schedule import ToolScheduleModel
from tool_platform.repositories.base import SQLAlchemyRepository


class ToolScheduleRepository(SQLAlchemyRepository[ToolScheduleModel]):
    model = ToolScheduleModel

    async def list_for_tool(self, tool_id: str) -> list[ToolScheduleModel]:
        stmt = select(ToolScheduleModel).where(ToolScheduleModel.tool_id == tool_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_due(self, *, as_of) -> list[ToolScheduleModel]:
        stmt = select(ToolScheduleModel).where(
            ToolScheduleModel.is_active.is_(True),
            ToolScheduleModel.status == "active",
            ToolScheduleModel.next_run_at.is_not(None),
            ToolScheduleModel.next_run_at <= as_of,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_active_for_workspace(self, workspace_id: str) -> list[ToolScheduleModel]:
        stmt = select(ToolScheduleModel).where(
            ToolScheduleModel.workspace_id == workspace_id, ToolScheduleModel.is_active.is_(True)
        )
        return list((await self.session.execute(stmt)).scalars().all())
