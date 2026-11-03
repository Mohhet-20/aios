from docs_platform.architecture.graph_rules import bfs_traverse


def test_bfs_traverse_direct_neighbors():
    adjacency = {"a": ["b", "c"], "b": [], "c": []}
    assert set(bfs_traverse(adjacency, "a")) == {"b", "c"}


def test_bfs_traverse_multi_hop():
    adjacency = {"a": ["b"], "b": ["c"], "c": ["d"], "d": []}
    assert bfs_traverse(adjacency, "a") == ["b", "c", "d"]


def test_bfs_traverse_respects_max_depth():
    adjacency = {"a": ["b"], "b": ["c"], "c": ["d"], "d": []}
    assert bfs_traverse(adjacency, "a", max_depth=1) == ["b"]


def test_bfs_traverse_handles_cycles():
    adjacency = {"a": ["b"], "b": ["a"]}
    assert bfs_traverse(adjacency, "a") == ["b"]


def test_bfs_traverse_no_neighbors():
    assert bfs_traverse({}, "isolated") == []
