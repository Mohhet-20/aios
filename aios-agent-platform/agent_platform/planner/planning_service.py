"""Task Planning engine: goal decomposition, subtask generation,
dependency-graph construction, priority assignment, execution ordering,
resource estimation, progress tracking, and adaptive replanning.
"""
from __future__ import annotations


from ai_core.bootstrap import AICoreContext

from agent_platform.core.exceptions import RecursionLimitExceededError
from agent_platform.domain.dependency_graph import validate_no_cycle
from agent_platform.domain.enums import TaskPriority, TaskStatus
from agent_platform.models.task import TaskDependencyModel, TaskModel
from agent_platform.planner.decomposition import decompose_goal
from agent_platform.planner.mappers import apply_task_domain_to_model, task_to_domain
from agent_platform.planner.ordering import topological_order
from agent_platform.repositories.registry import RepositoryRegistry


def _safe_priority(value: str) -> TaskPriority:
    try:
        return TaskPriority(value)
    except ValueError:
        return TaskPriority.NORMAL


class PlanningService:
    def __init__(self, repos: RepositoryRegistry, ai_core: AICoreContext, *, max_recursion_depth: int = 6):
        self.repos = repos
        self.ai_core = ai_core
        self.max_recursion_depth = max_recursion_depth

    # -- root task / goal creation ------------------------------------------------

    async def create_root_task(
        self, workspace_id: str, *, title: str, goal: str, created_by: str,
        priority: TaskPriority = TaskPriority.NORMAL, orchestration_strategy=None, context: dict | None = None,
    ) -> TaskModel:
        task = TaskModel(
            workspace_id=workspace_id, title=title, goal=goal, created_by=created_by, root_task_id="__pending__",
            priority=priority.value, context=context or {},
        )
        if orchestration_strategy is not None:
            task.orchestration_strategy = orchestration_strategy.value
        task = await self.repos.tasks.add(task)
        task.root_task_id = task.id  # a root task is its own root
        return await self.repos.tasks.update(task)

    # -- decomposition --------------------------------------------------------------

    async def decompose(self, task_id: str, *, max_subtasks: int = 8) -> list[TaskModel]:
        parent = await self.repos.tasks.get_or_404(task_id)
        if parent.depth + 1 > self.max_recursion_depth:
            raise RecursionLimitExceededError(
                f"Task '{task_id}' is at depth {parent.depth}; decomposing would exceed max_recursion_depth={self.max_recursion_depth}"
            )

        parent_entity = task_to_domain(parent)
        if parent_entity.status == TaskStatus.PENDING:
            parent_entity.start_planning()
            apply_task_domain_to_model(parent_entity, parent)
            await self.repos.tasks.update(parent)

        plan = await decompose_goal(self.ai_core, parent.goal, context=parent.context, max_subtasks=max_subtasks)

        created: list[TaskModel] = []
        for spec in plan.subtasks:
            priority = _safe_priority(spec.priority)
            child_model = TaskModel(
                workspace_id=parent.workspace_id, title=spec.title, goal=spec.goal, created_by=parent.created_by,
                parent_task_id=parent.id, root_task_id=parent.root_task_id, depth=parent.depth + 1, priority=priority.value,
                resource_estimate={"estimated_tokens": spec.estimated_tokens, "estimated_duration_seconds": spec.estimated_duration_seconds},
            )
            created.append(await self.repos.tasks.add(child_model))

        # Wire dependency edges using the returned batch-local indices,
        # validating each edge doesn't create a cycle before persisting it.
        existing_edges = await self.repos.task_dependencies.all_edges_for_root([parent.root_task_id])
        for i, spec in enumerate(plan.subtasks):
            for dep_index in spec.depends_on:
                if dep_index < 0 or dep_index >= len(created) or dep_index == i:
                    continue
                new_edge = (created[i].id, created[dep_index].id)
                validate_no_cycle(existing_edges, new_edge)
                existing_edges.append(new_edge)
                await self.repos.task_dependencies.add(TaskDependencyModel(task_id=new_edge[0], depends_on_task_id=new_edge[1]))

        return created

    # -- dependencies / ordering ----------------------------------------------------

    async def add_dependency(self, task_id: str, depends_on_task_id: str) -> TaskDependencyModel:
        parent_root = (await self.repos.tasks.get_or_404(task_id)).root_task_id
        existing_edges = await self.repos.task_dependencies.all_edges_for_root([parent_root])
        validate_no_cycle(existing_edges, (task_id, depends_on_task_id))
        return await self.repos.task_dependencies.add(TaskDependencyModel(task_id=task_id, depends_on_task_id=depends_on_task_id))

    async def execution_order(self, root_task_id: str) -> list[str]:
        subtasks = await self.repos.tasks.list_for_root(root_task_id)
        task_ids = [t.id for t in subtasks]
        priorities = {t.id: TaskPriority(t.priority) for t in subtasks}
        all_edges = await self.repos.task_dependencies.all_edges_for_root([root_task_id])
        relevant_edges = [(a, b) for a, b in all_edges if a in task_ids and b in task_ids]
        return topological_order(task_ids, relevant_edges, priorities)

    # -- resource estimation / progress ----------------------------------------------

    async def estimate_resources(self, root_task_id: str) -> dict:
        subtasks = await self.repos.tasks.list_for_root(root_task_id)
        children = [t for t in subtasks if t.id != root_task_id]
        total_tokens = sum((t.resource_estimate or {}).get("estimated_tokens", 0) for t in children)
        total_duration = sum((t.resource_estimate or {}).get("estimated_duration_seconds", 0.0) for t in children)
        return {"subtask_count": len(children), "estimated_tokens": total_tokens, "estimated_duration_seconds": total_duration}

    async def progress(self, root_task_id: str) -> dict:
        subtasks = await self.repos.tasks.list_for_root(root_task_id)
        children = [t for t in subtasks if t.id != root_task_id] or subtasks
        total = len(children)
        if total == 0:
            return {"total": 0, "completed": 0, "failed": 0, "in_progress": 0, "percent_complete": 0.0}
        completed = sum(1 for t in children if t.status == TaskStatus.COMPLETED.value)
        failed = sum(1 for t in children if t.status == TaskStatus.FAILED.value)
        in_progress = sum(1 for t in children if t.status == TaskStatus.IN_PROGRESS.value)
        return {
            "total": total, "completed": completed, "failed": failed, "in_progress": in_progress,
            "percent_complete": round(completed / total * 100, 2),
        }

    # -- adaptive replanning ------------------------------------------------------------

    async def replan(self, task_id: str, *, reason: str, max_subtasks: int = 8) -> list[TaskModel]:
        """Re-decomposes the remaining, not-yet-completed work under a
        task in light of a failure or new information — completed
        subtasks are left alone (their results feed back in as context),
        and any still-pending subtasks are cancelled in favor of the new
        plan so the graph doesn't end up with two competing plans."""
        parent = await self.repos.tasks.get_or_404(task_id)
        siblings = await self.repos.tasks.list_children(task_id)

        completed_results = [{"title": s.title, "result": s.result} for s in siblings if s.status == TaskStatus.COMPLETED.value]
        for sibling in siblings:
            if sibling.status in (TaskStatus.PENDING.value, TaskStatus.BLOCKED.value, TaskStatus.PLANNING.value):
                sibling_entity = task_to_domain(sibling)
                sibling_entity.cancel(f"superseded by replan: {reason}")
                apply_task_domain_to_model(sibling_entity, sibling)
                await self.repos.tasks.update(sibling)

        replan_context = dict(parent.context or {})
        replan_context["replanning_reason"] = reason
        replan_context["completed_so_far"] = completed_results
        parent.context = replan_context
        await self.repos.tasks.update(parent)

        return await self.decompose(task_id, max_subtasks=max_subtasks)
