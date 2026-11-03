from __future__ import annotations

from sqlalchemy import func, select

from prompt_platform.models.observability import PromptExecutionLogModel
from prompt_platform.repositories.base import SQLAlchemyRepository


class PromptExecutionLogRepository(SQLAlchemyRepository[PromptExecutionLogModel]):
    model = PromptExecutionLogModel

    async def list_for_prompt(self, prompt_id: str, *, limit: int = 100) -> list[PromptExecutionLogModel]:
        stmt = (
            select(PromptExecutionLogModel)
            .where(PromptExecutionLogModel.prompt_id == prompt_id)
            .order_by(PromptExecutionLogModel.created_at.desc())
            .limit(limit)
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def success_rate(self, prompt_id: str) -> float:
        total_stmt = select(func.count()).where(PromptExecutionLogModel.prompt_id == prompt_id)
        success_stmt = select(func.count()).where(
            PromptExecutionLogModel.prompt_id == prompt_id, PromptExecutionLogModel.success.is_(True)
        )
        total = (await self.session.execute(total_stmt)).scalar_one()
        if total == 0:
            return 0.0
        success = (await self.session.execute(success_stmt)).scalar_one()
        return round(success / total * 100, 2)
