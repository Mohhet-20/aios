from __future__ import annotations

from sqlalchemy import select

from agent_platform.models.task import TaskDependencyModel, TaskModel
from agent_platform.repositories.base import SQLAlchemyRepository


class TaskRepository(SQLAlchemyRepository[TaskModel]):
    model = TaskModel

    async def list_for_workspace(self, workspace_id: str, *, status: str | None = None) -> list[TaskModel]:
        filters = {"workspace_id": workspace_id}
        if status:
            filters["status"] = status
        return await self.list(filters=filters)

    async def list_children(self, parent_task_id: str) -> list[TaskModel]:
        stmt = select(TaskModel).where(TaskModel.parent_task_id == parent_task_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_root(self, root_task_id: str) -> list[TaskModel]:
        stmt = select(TaskModel).where(TaskModel.root_task_id == root_task_id).order_by(TaskModel.depth, TaskModel.created_at)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_agent(self, agent_id: str) -> list[TaskModel]:
        stmt = select(TaskModel).where(TaskModel.assigned_agent_id == agent_id).order_by(TaskModel.created_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())


class TaskDependencyRepository(SQLAlchemyRepository[TaskDependencyModel]):
    model = TaskDependencyModel

    async def list_for_task(self, task_id: str) -> list[TaskDependencyModel]:
        stmt = select(TaskDependencyModel).where(TaskDependencyModel.task_id == task_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def all_edges_for_root(self, root_task_ids: list[str]) -> list[tuple[str, str]]:
        stmt = select(TaskDependencyModel.task_id, TaskDependencyModel.depends_on_task_id)
        result = await self.session.execute(stmt)
        return [(row[0], row[1]) for row in result.all()]
