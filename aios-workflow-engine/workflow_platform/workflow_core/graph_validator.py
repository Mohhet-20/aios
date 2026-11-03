"""DAG validation for a workflow version's node/edge graph. A workflow
graph must be acyclic *except* through LOOP nodes, which are the one
sanctioned construct allowed to route back to an earlier node key (that's
what makes them a loop). Cycle detection therefore runs on a reduced
graph with LOOP-node-incident back-edges excluded, then a second pass
confirms every cycle that *does* exist passes through a LOOP node."""
from __future__ import annotations

from dataclasses import dataclass

from workflow_platform.core.exceptions import ValidationError, WorkflowCycleError
from workflow_platform.domain.enums import NodeType
from workflow_platform.node_library.registry import CYCLE_TOLERANT_NODE_TYPES


@dataclass
class GraphNode:
    node_key: str
    node_type: str


@dataclass
class GraphEdge:
    source_node_key: str
    target_node_key: str


def validate_graph(nodes: list[GraphNode], edges: list[GraphEdge]) -> None:
    if not nodes:
        raise ValidationError("a workflow version must have at least one node")

    keys_by_type: dict[str, list[str]] = {}
    for n in nodes:
        keys_by_type.setdefault(n.node_type, []).append(n.node_key)

    start_nodes = keys_by_type.get(NodeType.START.value, [])
    if len(start_nodes) != 1:
        raise ValidationError(f"a workflow version must have exactly one START node (found {len(start_nodes)})")
    if not keys_by_type.get(NodeType.END.value):
        raise ValidationError("a workflow version must have at least one END node")

    node_keys = {n.node_key for n in nodes}
    node_type_by_key = {n.node_key: n.node_type for n in nodes}
    seen_edge_keys: set[tuple[str, str]] = set()
    for e in edges:
        if e.source_node_key not in node_keys:
            raise ValidationError(f"edge references unknown source node '{e.source_node_key}'")
        if e.target_node_key not in node_keys:
            raise ValidationError(f"edge references unknown target node '{e.target_node_key}'")
        if e.source_node_key == e.target_node_key and node_type_by_key[e.source_node_key] not in CYCLE_TOLERANT_NODE_TYPES:
            raise WorkflowCycleError(f"node '{e.source_node_key}' has a self-loop but is not a cycle-tolerant node type")
        pair = (e.source_node_key, e.target_node_key)
        if pair in seen_edge_keys:
            raise ValidationError(f"duplicate edge {pair[0]} -> {pair[1]}")
        seen_edge_keys.add(pair)

    adjacency: dict[str, list[str]] = {n.node_key: [] for n in nodes}
    for e in edges:
        adjacency[e.source_node_key].append(e.target_node_key)

    _check_cycles(adjacency, node_type_by_key)
    _check_reachability(adjacency, start_nodes[0], node_keys)
    _check_routing_shape(nodes, edges)


# Node types allowed to fan out to more than one outgoing edge — everything
# else routes through exactly one outgoing edge, so the engine never has to
# guess which of several unconditional edges to follow.
_BRANCHING_NODE_TYPES = {
    NodeType.CONDITION.value, NodeType.DECISION.value, NodeType.PARALLEL_BRANCH.value, NodeType.LOOP.value,
}


def _check_routing_shape(nodes: list[GraphNode], edges: list[GraphEdge]) -> None:
    outgoing: dict[str, list[GraphEdge]] = {}
    for e in edges:
        outgoing.setdefault(e.source_node_key, []).append(e)

    for n in nodes:
        if n.node_type == NodeType.END.value:
            continue
        edges_out = outgoing.get(n.node_key, [])
        if n.node_type in _BRANCHING_NODE_TYPES:
            if not edges_out:
                raise ValidationError(f"branching node '{n.node_key}' ({n.node_type}) has no outgoing edges")
            continue
        if len(edges_out) > 1:
            raise ValidationError(
                f"node '{n.node_key}' ({n.node_type}) has {len(edges_out)} outgoing edges — only "
                f"CONDITION/DECISION/PARALLEL_BRANCH/LOOP nodes may have more than one"
            )


def _check_cycles(adjacency: dict[str, list[str]], node_type_by_key: dict[str, str]) -> None:
    WHITE, GRAY, BLACK = 0, 1, 2
    color: dict[str, int] = {k: WHITE for k in adjacency}

    def visit(u: str, path: list[str]) -> None:
        color[u] = GRAY
        path.append(u)
        for v in adjacency[u]:
            if color[v] == GRAY:
                cycle = path[path.index(v):] + [v]
                if not any(node_type_by_key.get(k) in CYCLE_TOLERANT_NODE_TYPES for k in cycle):
                    raise WorkflowCycleError(
                        f"graph contains an illegal cycle with no LOOP node: {' -> '.join(cycle)}"
                    )
            elif color[v] == WHITE:
                visit(v, path)
        path.pop()
        color[u] = BLACK

    for key in list(adjacency):
        if color[key] == WHITE:
            visit(key, [])


def _check_reachability(adjacency: dict[str, list[str]], start_key: str, node_keys: set[str]) -> None:
    visited: set[str] = set()
    stack = [start_key]
    while stack:
        cur = stack.pop()
        if cur in visited:
            continue
        visited.add(cur)
        stack.extend(adjacency.get(cur, []))
    unreachable = node_keys - visited
    if unreachable:
        raise ValidationError(f"nodes unreachable from START: {sorted(unreachable)}")
