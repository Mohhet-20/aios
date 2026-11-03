from __future__ import annotations

from sqlalchemy import select

from collaboration_platform.models.productivity import (
    BookmarkModel,
    ChecklistItemModel,
    ChecklistModel,
    PinnedItemModel,
    TaskModel,
)
from collaboration_platform.repositories.base import SQLAlchemyRepository


class TaskRepository(SQLAlchemyRepository[TaskModel]):
    model = TaskModel

    async def list_for_workspace(self, workspace_id: str, *, status: str | None = None) -> list[TaskModel]:
        stmt = select(TaskModel).where(TaskModel.workspace_id == workspace_id)
        if status:
            stmt = stmt.where(TaskModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_assignee(self, assignee_id: str, *, status: str | None = None) -> list[TaskModel]:
        stmt = select(TaskModel).where(TaskModel.assignee_id == assignee_id)
        if status:
            stmt = stmt.where(TaskModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())


class ChecklistRepository(SQLAlchemyRepository[ChecklistModel]):
    model = ChecklistModel

    async def list_for_task(self, task_id: str) -> list[ChecklistModel]:
        stmt = select(ChecklistModel).where(ChecklistModel.task_id == task_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_asset(self, asset_id: str) -> list[ChecklistModel]:
        stmt = select(ChecklistModel).where(ChecklistModel.asset_id == asset_id)
        return list((await self.session.execute(stmt)).scalars().all())


class ChecklistItemRepository(SQLAlchemyRepository[ChecklistItemModel]):
    model = ChecklistItemModel

    async def list_for_checklist(self, checklist_id: str) -> list[ChecklistItemModel]:
        stmt = select(ChecklistItemModel).where(ChecklistItemModel.checklist_id == checklist_id).order_by(ChecklistItemModel.position)
        return list((await self.session.execute(stmt)).scalars().all())


class BookmarkRepository(SQLAlchemyRepository[BookmarkModel]):
    model = BookmarkModel

    async def list_for_user(self, user_id: str) -> list[BookmarkModel]:
        stmt = select(BookmarkModel).where(BookmarkModel.user_id == user_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_user_and_asset(self, user_id: str, asset_id: str) -> BookmarkModel | None:
        stmt = select(BookmarkModel).where(BookmarkModel.user_id == user_id, BookmarkModel.asset_id == asset_id)
        return (await self.session.execute(stmt)).scalars().first()


class PinnedItemRepository(SQLAlchemyRepository[PinnedItemModel]):
    model = PinnedItemModel

    async def list_for_user_and_workspace(self, user_id: str, workspace_id: str) -> list[PinnedItemModel]:
        stmt = (
            select(PinnedItemModel)
            .where(PinnedItemModel.user_id == user_id, PinnedItemModel.workspace_id == workspace_id)
            .order_by(PinnedItemModel.position)
        )
        return list((await self.session.execute(stmt)).scalars().all())
