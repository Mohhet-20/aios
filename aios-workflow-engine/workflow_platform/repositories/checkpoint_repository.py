from __future__ import annotations

from sqlalchemy import select

from workflow_platform.models.checkpoint import CheckpointModel
from workflow_platform.repositories.base import SQLAlchemyRepository


class CheckpointRepository(SQLAlchemyRepository[CheckpointModel]):
    model = CheckpointModel

    async def list_for_execution(self, execution_id: str) -> list[CheckpointModel]:
        stmt = (
            select(CheckpointModel)
            .where(CheckpointModel.execution_id == execution_id)
            .order_by(CheckpointModel.sequence_number)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_latest_for_execution(self, execution_id: str) -> CheckpointModel | None:
        stmt = (
            select(CheckpointModel)
            .where(CheckpointModel.execution_id == execution_id)
            .order_by(CheckpointModel.sequence_number.desc())
        )
        return (await self.session.execute(stmt)).scalars().first()
