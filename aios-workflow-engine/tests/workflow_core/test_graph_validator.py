import pytest

from workflow_platform.core.exceptions import ValidationError, WorkflowCycleError
from workflow_platform.workflow_core.graph_validator import GraphEdge, GraphNode, validate_graph


def _linear_graph():
    nodes = [
        GraphNode("start", "start"),
        GraphNode("call_llm", "llm_call"),
        GraphNode("end", "end"),
    ]
    edges = [GraphEdge("start", "call_llm"), GraphEdge("call_llm", "end")]
    return nodes, edges


def test_valid_linear_graph_passes():
    nodes, edges = _linear_graph()
    validate_graph(nodes, edges)  # should not raise


def test_missing_start_node_rejected():
    nodes = [GraphNode("end", "end")]
    with pytest.raises(ValidationError):
        validate_graph(nodes, [])


def test_multiple_start_nodes_rejected():
    nodes = [GraphNode("start1", "start"), GraphNode("start2", "start"), GraphNode("end", "end")]
    with pytest.raises(ValidationError):
        validate_graph(nodes, [])


def test_missing_end_node_rejected():
    nodes = [GraphNode("start", "start")]
    with pytest.raises(ValidationError):
        validate_graph(nodes, [])


def test_dangling_edge_rejected():
    nodes, edges = _linear_graph()
    edges.append(GraphEdge("call_llm", "does_not_exist"))
    with pytest.raises(ValidationError):
        validate_graph(nodes, edges)


def test_illegal_cycle_rejected():
    nodes = [
        GraphNode("start", "start"),
        GraphNode("a", "llm_call"),
        GraphNode("b", "llm_call"),
        GraphNode("end", "end"),
    ]
    edges = [
        GraphEdge("start", "a"),
        GraphEdge("a", "b"),
        GraphEdge("b", "a"),  # illegal cycle: neither a nor b is a LOOP node
        GraphEdge("b", "end"),
    ]
    with pytest.raises(WorkflowCycleError):
        validate_graph(nodes, edges)


def test_loop_node_cycle_is_allowed():
    nodes = [
        GraphNode("start", "start"),
        GraphNode("loop1", "loop"),
        GraphNode("body", "llm_call"),
        GraphNode("end", "end"),
    ]
    edges = [
        GraphEdge("start", "loop1"),
        GraphEdge("loop1", "body"),
        GraphEdge("body", "loop1"),  # cycle back through the LOOP node — allowed
        GraphEdge("loop1", "end"),
    ]
    validate_graph(nodes, edges)  # should not raise


def test_unreachable_node_rejected():
    nodes, edges = _linear_graph()
    nodes.append(GraphNode("orphan", "llm_call"))
    with pytest.raises(ValidationError):
        validate_graph(nodes, edges)


def test_self_loop_on_non_loop_node_rejected():
    nodes = [GraphNode("start", "start"), GraphNode("a", "llm_call"), GraphNode("end", "end")]
    edges = [GraphEdge("start", "a"), GraphEdge("a", "a"), GraphEdge("a", "end")]
    with pytest.raises(WorkflowCycleError):
        validate_graph(nodes, edges)
