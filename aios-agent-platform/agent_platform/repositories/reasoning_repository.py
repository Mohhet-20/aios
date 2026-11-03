from __future__ import annotations

from sqlalchemy import select

from agent_platform.models.reasoning import ReasoningTraceModel, ReflectionModel
from agent_platform.repositories.base import SQLAlchemyRepository


class ReasoningTraceRepository(SQLAlchemyRepository[ReasoningTraceModel]):
    model = ReasoningTraceModel

    async def list_for_execution(self, execution_id: str) -> list[ReasoningTraceModel]:
        stmt = select(ReasoningTraceModel).where(ReasoningTraceModel.execution_id == execution_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_task(self, task_id: str) -> list[ReasoningTraceModel]:
        stmt = select(ReasoningTraceModel).where(ReasoningTraceModel.task_id == task_id).order_by(ReasoningTraceModel.created_at)
        return list((await self.session.execute(stmt)).scalars().all())


class ReflectionRepository(SQLAlchemyRepository[ReflectionModel]):
    model = ReflectionModel

    async def list_for_execution(self, execution_id: str) -> list[ReflectionModel]:
        stmt = select(ReflectionModel).where(ReflectionModel.execution_id == execution_id).order_by(ReflectionModel.iteration)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_task(self, task_id: str) -> list[ReflectionModel]:
        stmt = select(ReflectionModel).where(ReflectionModel.task_id == task_id).order_by(ReflectionModel.created_at)
        return list((await self.session.execute(stmt)).scalars().all())
