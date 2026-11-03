"""TaskService: lightweight task assignments scoped to a workspace
(and optionally a project/asset), backed by the guarded `Task` domain
entity for todo -> in_progress -> done/cancelled."""
from __future__ import annotations

from collaboration_platform.domain.entities import Task
from collaboration_platform.domain.enums import TaskStatus
from collaboration_platform.models.productivity import TaskModel
from collaboration_platform.repositories.registry import RepositoryRegistry


def _task_to_domain(model: TaskModel) -> Task:
    return Task(id=model.id, title=model.title, status=TaskStatus(model.status), completed_at=model.completed_at)


def _apply_task_domain(entity: Task, model: TaskModel) -> None:
    model.status = entity.status.value
    model.completed_at = entity.completed_at


class TaskService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_task(
        self, workspace_id: str, *, title: str, created_by: str, project_id: str | None = None, asset_id: str | None = None,
        assignee_id: str | None = None, description: str | None = None, due_date=None,
    ) -> TaskModel:
        await self.repos.workspaces.get_or_404(workspace_id)
        return await self.repos.tasks.add(TaskModel(
            workspace_id=workspace_id, project_id=project_id, asset_id=asset_id, title=title, description=description,
            assignee_id=assignee_id, due_date=due_date, created_by=created_by,
        ))

    async def assign(self, task_id: str, assignee_id: str | None) -> TaskModel:
        task = await self.repos.tasks.get_or_404(task_id)
        task.assignee_id = assignee_id
        return await self.repos.tasks.update(task)

    async def start(self, task_id: str) -> TaskModel:
        return await self._apply_transition(task_id, "start")

    async def complete(self, task_id: str) -> TaskModel:
        return await self._apply_transition(task_id, "complete")

    async def reopen(self, task_id: str) -> TaskModel:
        return await self._apply_transition(task_id, "reopen")

    async def cancel(self, task_id: str) -> TaskModel:
        return await self._apply_transition(task_id, "cancel")

    async def _apply_transition(self, task_id: str, method_name: str) -> TaskModel:
        task = await self.repos.tasks.get_or_404(task_id)
        entity = _task_to_domain(task)
        getattr(entity, method_name)()
        _apply_task_domain(entity, task)
        return await self.repos.tasks.update(task)

    async def list_for_workspace(self, workspace_id: str, *, status: str | None = None) -> list[TaskModel]:
        return await self.repos.tasks.list_for_workspace(workspace_id, status=status)

    async def list_for_assignee(self, assignee_id: str, *, status: str | None = None) -> list[TaskModel]:
        return await self.repos.tasks.list_for_assignee(assignee_id, status=status)
