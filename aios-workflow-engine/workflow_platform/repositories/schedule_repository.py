from __future__ import annotations

from sqlalchemy import select

from workflow_platform.models.schedule import ScheduleModel
from workflow_platform.repositories.base import SQLAlchemyRepository


class ScheduleRepository(SQLAlchemyRepository[ScheduleModel]):
    model = ScheduleModel

    async def list_for_workflow(self, workflow_id: str) -> list[ScheduleModel]:
        stmt = select(ScheduleModel).where(ScheduleModel.workflow_id == workflow_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_due(self, *, as_of) -> list[ScheduleModel]:
        stmt = select(ScheduleModel).where(
            ScheduleModel.is_active.is_(True),
            ScheduleModel.status == "active",
            ScheduleModel.next_run_at.is_not(None),
            ScheduleModel.next_run_at <= as_of,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_active_for_workspace(self, workspace_id: str) -> list[ScheduleModel]:
        stmt = select(ScheduleModel).where(
            ScheduleModel.workspace_id == workspace_id, ScheduleModel.is_active.is_(True)
        )
        return list((await self.session.execute(stmt)).scalars().all())
