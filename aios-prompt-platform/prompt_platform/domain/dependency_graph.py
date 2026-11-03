"""Pure dependency-graph validation: a prompt composing/referencing/
chaining other prompts must not form a cycle, or rendering it would
recurse forever. This is deliberately a free function over plain edge
tuples — no ORM/session access — so it's trivial to unit test and cannot
accidentally issue a query mid-validation.
"""
from __future__ import annotations

from prompt_platform.core.exceptions import DependencyCycleError


def would_create_cycle(existing_edges: list[tuple[str, str]], new_edge: tuple[str, str]) -> bool:
    """`existing_edges`/`new_edge` are (prompt_id, depends_on_prompt_id)
    pairs. Returns True if adding `new_edge` would create a cycle
    reachable from `new_edge[1]` back to `new_edge[0]`."""
    graph: dict[str, list[str]] = {}
    for src, dst in [*existing_edges, new_edge]:
        graph.setdefault(src, []).append(dst)

    start = new_edge[1]
    target = new_edge[0]
    visited: set[str] = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node == target:
            return True
        if node in visited:
            continue
        visited.add(node)
        stack.extend(graph.get(node, []))
    return False


def validate_no_cycle(existing_edges: list[tuple[str, str]], new_edge: tuple[str, str]) -> None:
    if new_edge[0] == new_edge[1]:
        raise DependencyCycleError(f"prompt {new_edge[0]} cannot depend on itself")
    if would_create_cycle(existing_edges, new_edge):
        raise DependencyCycleError(f"adding dependency {new_edge[0]} -> {new_edge[1]} would create a cycle")
