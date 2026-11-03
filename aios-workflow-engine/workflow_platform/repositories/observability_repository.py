from __future__ import annotations

from sqlalchemy import select

from workflow_platform.models.observability import ExecutionLogModel
from workflow_platform.repositories.base import SQLAlchemyRepository


class ExecutionLogRepository(SQLAlchemyRepository[ExecutionLogModel]):
    model = ExecutionLogModel

    async def list_for_execution(self, execution_id: str, *, level: str | None = None) -> list[ExecutionLogModel]:
        stmt = select(ExecutionLogModel).where(ExecutionLogModel.execution_id == execution_id)
        if level:
            stmt = stmt.where(ExecutionLogModel.level == level)
        stmt = stmt.order_by(ExecutionLogModel.created_at)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_node_execution(self, node_execution_id: str) -> list[ExecutionLogModel]:
        stmt = select(ExecutionLogModel).where(ExecutionLogModel.node_execution_id == node_execution_id).order_by(
            ExecutionLogModel.created_at
        )
        return list((await self.session.execute(stmt)).scalars().all())
