"""Pure-function DAG cycle detection for task dependency edges — reused
verbatim in spirit from the Prompt Platform's dependency graph, since
"does adding this edge create a cycle" is the same problem whether the
nodes are prompts or tasks."""
from __future__ import annotations

from agent_platform.core.exceptions import DependencyCycleError


def would_create_cycle(existing_edges: list[tuple[str, str]], new_edge: tuple[str, str]) -> bool:
    """`existing_edges`/`new_edge` are (task_id, depends_on_task_id) pairs.
    Returns True if adding `new_edge` would create a cycle reachable from
    `depends_on_task_id` back to `task_id`."""
    task_id, depends_on_task_id = new_edge
    if task_id == depends_on_task_id:
        return True

    adjacency: dict[str, list[str]] = {}
    for src, dst in [*existing_edges, new_edge]:
        adjacency.setdefault(src, []).append(dst)

    visited: set[str] = set()

    def dfs(node: str, target: str) -> bool:
        if node == target:
            return True
        if node in visited:
            return False
        visited.add(node)
        return any(dfs(nxt, target) for nxt in adjacency.get(node, []))

    return dfs(depends_on_task_id, task_id)


def validate_no_cycle(existing_edges: list[tuple[str, str]], new_edge: tuple[str, str]) -> None:
    if would_create_cycle(existing_edges, new_edge):
        raise DependencyCycleError(f"Adding dependency {new_edge} would create a cycle in the task graph")
