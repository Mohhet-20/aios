from __future__ import annotations

from sqlalchemy import select

from tool_platform.models.checkpoint import ExecutionCheckpointModel
from tool_platform.repositories.base import SQLAlchemyRepository


class ExecutionCheckpointRepository(SQLAlchemyRepository[ExecutionCheckpointModel]):
    model = ExecutionCheckpointModel

    async def list_for_execution(self, execution_id: str) -> list[ExecutionCheckpointModel]:
        stmt = select(ExecutionCheckpointModel).where(ExecutionCheckpointModel.execution_id == execution_id).order_by(
            ExecutionCheckpointModel.sequence_number
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_latest(self, execution_id: str) -> ExecutionCheckpointModel | None:
        stmt = select(ExecutionCheckpointModel).where(ExecutionCheckpointModel.execution_id == execution_id).order_by(
            ExecutionCheckpointModel.sequence_number.desc()
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def get_by_sequence(self, execution_id: str, sequence_number: int) -> ExecutionCheckpointModel | None:
        stmt = select(ExecutionCheckpointModel).where(
            ExecutionCheckpointModel.execution_id == execution_id,
            ExecutionCheckpointModel.sequence_number == sequence_number,
        )
        return (await self.session.execute(stmt)).scalars().first()
