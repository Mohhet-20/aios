from __future__ import annotations

from sqlalchemy import select

from tool_platform.models.observability import ExecutionLogModel
from tool_platform.repositories.base import SQLAlchemyRepository


class ExecutionLogRepository(SQLAlchemyRepository[ExecutionLogModel]):
    model = ExecutionLogModel

    async def list_for_execution(self, execution_id: str, *, level: str | None = None) -> list[ExecutionLogModel]:
        stmt = select(ExecutionLogModel).where(ExecutionLogModel.execution_id == execution_id)
        if level:
            stmt = stmt.where(ExecutionLogModel.level == level)
        stmt = stmt.order_by(ExecutionLogModel.created_at)
        return list((await self.session.execute(stmt)).scalars().all())
