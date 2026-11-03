"""Execution ordering: topological sort (Kahn's algorithm) over a task's
dependency edges, with priority as the tiebreaker among tasks that are
simultaneously ready to run — so "no dependencies" doesn't mean
"arbitrary order" when priorities differ.
"""
from __future__ import annotations

from agent_platform.core.exceptions import DependencyCycleError
from agent_platform.domain.enums import TaskPriority

_PRIORITY_RANK = {TaskPriority.CRITICAL: 0, TaskPriority.HIGH: 1, TaskPriority.NORMAL: 2, TaskPriority.LOW: 3}


def topological_order(task_ids: list[str], edges: list[tuple[str, str]], priorities: dict[str, TaskPriority] | None = None) -> list[str]:
    """`edges` are (task_id, depends_on_task_id) pairs. Returns `task_ids`
    ordered so every task appears after everything it depends on."""
    priorities = priorities or {}
    in_degree: dict[str, int] = {tid: 0 for tid in task_ids}
    dependents: dict[str, list[str]] = {tid: [] for tid in task_ids}

    for task_id, depends_on in edges:
        if task_id not in in_degree or depends_on not in in_degree:
            continue  # edge references a task outside this batch — ignore
        in_degree[task_id] += 1
        dependents[depends_on].append(task_id)

    ready = [tid for tid, deg in in_degree.items() if deg == 0]
    ready.sort(key=lambda tid: _PRIORITY_RANK.get(priorities.get(tid, TaskPriority.NORMAL), 2))

    ordered: list[str] = []
    while ready:
        ready.sort(key=lambda tid: _PRIORITY_RANK.get(priorities.get(tid, TaskPriority.NORMAL), 2))
        current = ready.pop(0)
        ordered.append(current)
        for dependent in dependents[current]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                ready.append(dependent)

    if len(ordered) != len(task_ids):
        raise DependencyCycleError("Task graph contains a cycle — cannot compute a valid execution order")
    return ordered
