from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select

from agent_platform.models.execution import AgentExecutionModel, ExecutionCheckpointModel
from agent_platform.repositories.base import SQLAlchemyRepository


class AgentExecutionRepository(SQLAlchemyRepository[AgentExecutionModel]):
    model = AgentExecutionModel

    async def list_for_agent(self, agent_id: str, *, limit: int = 100) -> list[AgentExecutionModel]:
        stmt = select(AgentExecutionModel).where(AgentExecutionModel.agent_id == agent_id).order_by(
            AgentExecutionModel.started_at.desc()
        ).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_task(self, task_id: str) -> list[AgentExecutionModel]:
        stmt = select(AgentExecutionModel).where(AgentExecutionModel.task_id == task_id).order_by(AgentExecutionModel.started_at)
        return list((await self.session.execute(stmt)).scalars().all())

    async def success_rate(self, agent_id: str) -> float:
        total_stmt = select(func.count()).where(AgentExecutionModel.agent_id == agent_id)
        success_stmt = select(func.count()).where(AgentExecutionModel.agent_id == agent_id, AgentExecutionModel.success.is_(True))
        total = (await self.session.execute(total_stmt)).scalar_one()
        if total == 0:
            return 0.0
        success = (await self.session.execute(success_stmt)).scalar_one()
        return round(success / total * 100, 2)

    async def count_recent_by_triggerer(self, triggered_by: str, *, since: datetime) -> int:
        stmt = select(func.count()).where(AgentExecutionModel.triggered_by == triggered_by, AgentExecutionModel.started_at >= since)
        return (await self.session.execute(stmt)).scalar_one()

    async def count_running_for_agent(self, agent_id: str) -> int:
        stmt = select(func.count()).where(AgentExecutionModel.agent_id == agent_id, AgentExecutionModel.status == "running")
        return (await self.session.execute(stmt)).scalar_one()


class ExecutionCheckpointRepository(SQLAlchemyRepository[ExecutionCheckpointModel]):
    model = ExecutionCheckpointModel

    async def list_for_task(self, task_id: str) -> list[ExecutionCheckpointModel]:
        stmt = select(ExecutionCheckpointModel).where(ExecutionCheckpointModel.task_id == task_id).order_by(ExecutionCheckpointModel.created_at)
        return list((await self.session.execute(stmt)).scalars().all())

    async def latest_for_task(self, task_id: str) -> ExecutionCheckpointModel | None:
        stmt = select(ExecutionCheckpointModel).where(ExecutionCheckpointModel.task_id == task_id).order_by(ExecutionCheckpointModel.created_at.desc())
        return (await self.session.execute(stmt)).scalars().first()
