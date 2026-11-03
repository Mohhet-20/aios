import pytest

from memory_platform.knowledge_graph.graph_service import KnowledgeGraphService
from memory_platform.models.workspace import WorkspaceModel


async def _workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(id="ws-1", name="Acme", slug="acme", organization_id="org-1"))


@pytest.mark.asyncio
async def test_upsert_entity_is_idempotent_by_ref(repos):
    await _workspace(repos)
    svc = KnowledgeGraphService(repos)
    a1 = await svc.upsert_entity(workspace_id="ws-1", entity_type="document", name="Doc A", ref_id="doc-1")
    a2 = await svc.upsert_entity(workspace_id="ws-1", entity_type="document", name="Doc A renamed", ref_id="doc-1")
    assert a1.id == a2.id
    assert a2.name == "Doc A renamed"


@pytest.mark.asyncio
async def test_upsert_entity_without_ref_always_creates_new(repos):
    await _workspace(repos)
    svc = KnowledgeGraphService(repos)
    c1 = await svc.upsert_entity(workspace_id="ws-1", entity_type="concept", name="Distributed Systems")
    c2 = await svc.upsert_entity(workspace_id="ws-1", entity_type="concept", name="Distributed Systems")
    assert c1.id != c2.id


@pytest.mark.asyncio
async def test_link_and_neighbors(repos):
    await _workspace(repos)
    svc = KnowledgeGraphService(repos)
    a = await svc.upsert_entity(workspace_id="ws-1", entity_type="document", name="A")
    b = await svc.upsert_entity(workspace_id="ws-1", entity_type="document", name="B")
    c = await svc.upsert_entity(workspace_id="ws-1", entity_type="document", name="C")
    await svc.link(workspace_id="ws-1", source_entity_id=a.id, target_entity_id=b.id, relation_type="related_to")
    await svc.link(workspace_id="ws-1", source_entity_id=c.id, target_entity_id=a.id, relation_type="mentions")

    out_neighbors = await svc.neighbors(a.id, direction="out")
    assert {n.id for n in out_neighbors} == {b.id}
    in_neighbors = await svc.neighbors(a.id, direction="in")
    assert {n.id for n in in_neighbors} == {c.id}
    both = await svc.neighbors(a.id, direction="both")
    assert {n.id for n in both} == {b.id, c.id}


@pytest.mark.asyncio
async def test_neighbors_filtered_by_relation_type(repos):
    await _workspace(repos)
    svc = KnowledgeGraphService(repos)
    a = await svc.upsert_entity(workspace_id="ws-1", entity_type="document", name="A")
    b = await svc.upsert_entity(workspace_id="ws-1", entity_type="document", name="B")
    c = await svc.upsert_entity(workspace_id="ws-1", entity_type="document", name="C")
    await svc.link(workspace_id="ws-1", source_entity_id=a.id, target_entity_id=b.id, relation_type="depends_on")
    await svc.link(workspace_id="ws-1", source_entity_id=a.id, target_entity_id=c.id, relation_type="related_to")

    deps = await svc.dependencies(a.id)
    assert {d.id for d in deps} == {b.id}


@pytest.mark.asyncio
async def test_traverse_multi_hop_bfs_respects_max_depth(repos):
    await _workspace(repos)
    svc = KnowledgeGraphService(repos)
    nodes = [await svc.upsert_entity(workspace_id="ws-1", entity_type="concept", name=f"n{i}") for i in range(5)]
    # chain: 0 -> 1 -> 2 -> 3 -> 4
    for i in range(4):
        await svc.link(workspace_id="ws-1", source_entity_id=nodes[i].id, target_entity_id=nodes[i + 1].id, relation_type="related_to")

    result = await svc.traverse(nodes[0].id, max_depth=2, direction="out")
    assert result.depth_by_entity_id[nodes[0].id] == 0
    assert result.depth_by_entity_id[nodes[1].id] == 1
    assert result.depth_by_entity_id[nodes[2].id] == 2
    assert nodes[3].id not in result.depth_by_entity_id  # beyond max_depth
    assert nodes[4].id not in result.depth_by_entity_id


@pytest.mark.asyncio
async def test_traverse_is_cycle_safe(repos):
    await _workspace(repos)
    svc = KnowledgeGraphService(repos)
    a = await svc.upsert_entity(workspace_id="ws-1", entity_type="concept", name="A")
    b = await svc.upsert_entity(workspace_id="ws-1", entity_type="concept", name="B")
    await svc.link(workspace_id="ws-1", source_entity_id=a.id, target_entity_id=b.id, relation_type="related_to")
    await svc.link(workspace_id="ws-1", source_entity_id=b.id, target_entity_id=a.id, relation_type="related_to")

    result = await svc.traverse(a.id, max_depth=10, direction="out")
    assert set(result.visited_entity_ids) == {a.id, b.id}


@pytest.mark.asyncio
async def test_shortest_path_finds_fewest_hops(repos):
    await _workspace(repos)
    svc = KnowledgeGraphService(repos)
    nodes = [await svc.upsert_entity(workspace_id="ws-1", entity_type="concept", name=f"n{i}") for i in range(4)]
    # 0 -> 1 -> 2 -> 3 and a shortcut 0 -> 3 does NOT exist; also add unrelated 0->2 direct isn't present
    for i in range(3):
        await svc.link(workspace_id="ws-1", source_entity_id=nodes[i].id, target_entity_id=nodes[i + 1].id, relation_type="related_to")

    path = await svc.shortest_path(nodes[0].id, nodes[3].id)
    assert path == [nodes[0].id, nodes[1].id, nodes[2].id, nodes[3].id]


@pytest.mark.asyncio
async def test_shortest_path_prefers_shortcut(repos):
    await _workspace(repos)
    svc = KnowledgeGraphService(repos)
    nodes = [await svc.upsert_entity(workspace_id="ws-1", entity_type="concept", name=f"n{i}") for i in range(4)]
    for i in range(3):
        await svc.link(workspace_id="ws-1", source_entity_id=nodes[i].id, target_entity_id=nodes[i + 1].id, relation_type="related_to")
    await svc.link(workspace_id="ws-1", source_entity_id=nodes[0].id, target_entity_id=nodes[3].id, relation_type="related_to")

    path = await svc.shortest_path(nodes[0].id, nodes[3].id)
    assert path == [nodes[0].id, nodes[3].id]


@pytest.mark.asyncio
async def test_shortest_path_returns_none_when_unreachable(repos):
    await _workspace(repos)
    svc = KnowledgeGraphService(repos)
    a = await svc.upsert_entity(workspace_id="ws-1", entity_type="concept", name="A")
    b = await svc.upsert_entity(workspace_id="ws-1", entity_type="concept", name="B")
    path = await svc.shortest_path(a.id, b.id, max_depth=3)
    assert path is None


@pytest.mark.asyncio
async def test_delete_entity_cascades_relationships(repos):
    await _workspace(repos)
    svc = KnowledgeGraphService(repos)
    a = await svc.upsert_entity(workspace_id="ws-1", entity_type="concept", name="A")
    b = await svc.upsert_entity(workspace_id="ws-1", entity_type="concept", name="B")
    rel = await svc.link(workspace_id="ws-1", source_entity_id=a.id, target_entity_id=b.id, relation_type="related_to")
    await svc.delete_entity(a.id)
    remaining = await repos.kg_relationships.get(rel.id)
    assert remaining is None


@pytest.mark.asyncio
async def test_search_entities_by_name(repos):
    await _workspace(repos)
    svc = KnowledgeGraphService(repos)
    await svc.upsert_entity(workspace_id="ws-1", entity_type="concept", name="Distributed Consensus")
    await svc.upsert_entity(workspace_id="ws-1", entity_type="concept", name="Unrelated Thing")
    results = await svc.search_entities("ws-1", "consensus")
    assert len(results) == 1
    assert results[0].name == "Distributed Consensus"
