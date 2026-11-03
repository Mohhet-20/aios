from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select

from tool_platform.models.execution import ToolExecutionModel
from tool_platform.repositories.base import SQLAlchemyRepository


class ToolExecutionRepository(SQLAlchemyRepository[ToolExecutionModel]):
    model = ToolExecutionModel

    async def count_recent_by_triggerer(self, triggered_by: str, *, since: datetime) -> int:
        """Backs PolicyEngine's rate limiting — counts calls *initiated*
        (created_at, not started_at) in the trailing window, since a
        principal spamming calls that then queue up should still trip
        the limiter even before any of them start running."""
        stmt = select(func.count()).where(
            ToolExecutionModel.triggered_by == triggered_by, ToolExecutionModel.created_at >= since,
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def list_for_tool(self, tool_id: str, *, status: str | None = None, limit: int = 100) -> list[ToolExecutionModel]:
        stmt = select(ToolExecutionModel).where(ToolExecutionModel.tool_id == tool_id)
        if status:
            stmt = stmt.where(ToolExecutionModel.status == status)
        stmt = stmt.order_by(ToolExecutionModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_workspace(self, workspace_id: str, *, status: str | None = None, limit: int = 200) -> list[ToolExecutionModel]:
        stmt = select(ToolExecutionModel).where(ToolExecutionModel.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(ToolExecutionModel.status == status)
        stmt = stmt.order_by(ToolExecutionModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_user(self, triggered_by: str, *, limit: int = 20) -> list[ToolExecutionModel]:
        """Backs Tool Discovery's "Recently Used" — see discovery module docstring."""
        stmt = select(ToolExecutionModel).where(ToolExecutionModel.triggered_by == triggered_by).order_by(
            ToolExecutionModel.created_at.desc()
        ).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_children(self, parent_execution_id: str) -> list[ToolExecutionModel]:
        stmt = select(ToolExecutionModel).where(ToolExecutionModel.parent_execution_id == parent_execution_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_active_for_tool(self, tool_id: str) -> int:
        stmt = select(func.count()).where(
            ToolExecutionModel.tool_id == tool_id,
            ToolExecutionModel.status.in_(["pending", "queued", "running", "retrying"]),
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def count_active_for_workspace(self, workspace_id: str) -> int:
        stmt = select(func.count()).where(
            ToolExecutionModel.workspace_id == workspace_id,
            ToolExecutionModel.status.in_(["pending", "queued", "running", "retrying"]),
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def list_by_status(self, status: str, *, limit: int = 500) -> list[ToolExecutionModel]:
        stmt = select(ToolExecutionModel).where(ToolExecutionModel.status == status).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_stalled_running(self, *, older_than) -> list[ToolExecutionModel]:
        stmt = select(ToolExecutionModel).where(
            ToolExecutionModel.status == "running", ToolExecutionModel.started_at.is_not(None),
            ToolExecutionModel.started_at <= older_than,
        )
        return list((await self.session.execute(stmt)).scalars().all())
