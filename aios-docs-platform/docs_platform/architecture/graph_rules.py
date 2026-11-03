"""Pure BFS traversal over a diagram's `related_refs` adjacency — no
DB/service imports. Mirrors the lineage-traversal pattern used
elsewhere in the AIOS platform family (e.g. the Analytics Platform's
data-lineage BFS): a capped depth keeps a pathological cycle or an
unexpectedly dense graph from turning "show me what's related to this
diagram" into an unbounded walk."""
from __future__ import annotations

DEFAULT_MAX_TRAVERSAL_DEPTH = 10


def bfs_traverse(adjacency: dict[str, list[str]], start: str, *, max_depth: int = DEFAULT_MAX_TRAVERSAL_DEPTH) -> list[str]:
    """Returns every node reachable from `start` (excluding `start`
    itself), breadth-first, without exceeding `max_depth` hops or
    revisiting a node already seen."""
    visited: set[str] = {start}
    result: list[str] = []
    frontier = [start]
    depth = 0
    while frontier and depth < max_depth:
        next_frontier: list[str] = []
        for node in frontier:
            for neighbor in adjacency.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    result.append(neighbor)
                    next_frontier.append(neighbor)
        frontier = next_frontier
        depth += 1
    return result
