from __future__ import annotations

from sqlalchemy import select

from agent_platform.models.message import MessageModel, SharedWorkspaceEntryModel
from agent_platform.repositories.base import SQLAlchemyRepository


class MessageRepository(SQLAlchemyRepository[MessageModel]):
    model = MessageModel

    async def list_for_task(self, task_id: str, *, limit: int = 500) -> list[MessageModel]:
        stmt = select(MessageModel).where(MessageModel.task_id == task_id).order_by(MessageModel.created_at).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_agent(self, agent_id: str, *, limit: int = 100) -> list[MessageModel]:
        stmt = select(MessageModel).where(
            (MessageModel.from_agent_id == agent_id) | (MessageModel.to_agent_id == agent_id)
        ).order_by(MessageModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_broadcasts_for_task(self, task_id: str) -> list[MessageModel]:
        stmt = select(MessageModel).where(MessageModel.task_id == task_id, MessageModel.to_agent_id.is_(None)).order_by(MessageModel.created_at)
        return list((await self.session.execute(stmt)).scalars().all())


class SharedWorkspaceRepository(SQLAlchemyRepository[SharedWorkspaceEntryModel]):
    model = SharedWorkspaceEntryModel

    async def get_by_key(self, task_id: str, key: str) -> SharedWorkspaceEntryModel | None:
        stmt = select(SharedWorkspaceEntryModel).where(SharedWorkspaceEntryModel.task_id == task_id, SharedWorkspaceEntryModel.key == key)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_task(self, task_id: str) -> list[SharedWorkspaceEntryModel]:
        stmt = select(SharedWorkspaceEntryModel).where(SharedWorkspaceEntryModel.task_id == task_id)
        return list((await self.session.execute(stmt)).scalars().all())
