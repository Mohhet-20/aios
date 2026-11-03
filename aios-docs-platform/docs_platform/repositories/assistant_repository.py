from __future__ import annotations

from sqlalchemy import select

from docs_platform.models.assistant import AssistantSessionModel
from docs_platform.repositories.base import SQLAlchemyRepository


class AssistantSessionRepository(SQLAlchemyRepository[AssistantSessionModel]):
    model = AssistantSessionModel

    async def list_for_user(self, tenant_id: str, user_id: str, *, limit: int = 50) -> list[AssistantSessionModel]:
        stmt = select(AssistantSessionModel).where(
            AssistantSessionModel.tenant_id == tenant_id, AssistantSessionModel.user_id == user_id,
        ).order_by(AssistantSessionModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_recent(self, tenant_id: str, *, limit: int = 100) -> list[AssistantSessionModel]:
        stmt = select(AssistantSessionModel).where(
            AssistantSessionModel.tenant_id == tenant_id,
        ).order_by(AssistantSessionModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
