import pytest

from memory_platform.vector_store.vector_platform_service import VectorPlatformService


@pytest.mark.asyncio
async def test_embed_and_index_persists_records_and_upserts_vectors(repos, scripted_ai_core):
    ai_core, provider = scripted_ai_core
    svc = VectorPlatformService(repos, ai_core)
    items = [("chunk-1", "The quick brown fox", {"document_id": "doc-1"}), ("chunk-2", "jumps over the lazy dog", {"document_id": "doc-1"})]
    records = await svc.embed_and_index(workspace_id="ws-1", source_type="document_chunk", items=items)
    assert len(records) == 2
    assert {r.source_id for r in records} == {"chunk-1", "chunk-2"}
    assert all(r.vector_store_index == "default" for r in records)
    assert all(r.embedding_version == "v1" for r in records)


@pytest.mark.asyncio
async def test_embed_and_index_batches_large_item_lists(repos, scripted_ai_core):
    ai_core, provider = scripted_ai_core
    svc = VectorPlatformService(repos, ai_core)
    items = [(f"chunk-{i}", f"content number {i}", {}) for i in range(25)]
    records = await svc.embed_and_index(workspace_id="ws-1", source_type="document_chunk", items=items, batch_size=10)
    assert len(records) == 25
    assert provider.calls == 3  # 10 + 10 + 5 -> three batched embed calls


@pytest.mark.asyncio
async def test_incremental_update_indexes_single_item(repos, scripted_ai_core):
    ai_core, provider = scripted_ai_core
    svc = VectorPlatformService(repos, ai_core)
    record = await svc.incremental_update(workspace_id="ws-1", source_type="memory_entry", source_id="mem-1", text="updated content")
    assert record.source_id == "mem-1"
    assert record.source_type == "memory_entry"


@pytest.mark.asyncio
async def test_reindex_with_version_bump_keeps_history(repos, scripted_ai_core):
    ai_core, provider = scripted_ai_core
    svc = VectorPlatformService(repos, ai_core)
    v1 = await svc.reindex_with_version_bump(workspace_id="ws-1", source_type="knowledge_item", source_id="ki-1", text="v1 content")
    v2 = await svc.reindex_with_version_bump(workspace_id="ws-1", source_type="knowledge_item", source_id="ki-1", text="v2 content")
    assert v1.embedding_version == "v1"
    assert v2.embedding_version == "v2"
    history = await repos.embedding_records.list_for_sources("knowledge_item", ["ki-1"])
    assert {h.embedding_version for h in history} == {"v1", "v2"}


@pytest.mark.asyncio
async def test_similarity_search_returns_matches_ranked_by_similarity(repos, scripted_ai_core):
    from tests.conftest import make_embedding_response

    ai_core, provider = scripted_ai_core
    svc = VectorPlatformService(repos, ai_core)
    # index two items with distinguishable vectors
    provider.push(make_embedding_response([[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]))
    await svc.embed_and_index(workspace_id="ws-1", source_type="document_chunk", items=[("a", "text a", {}), ("b", "text b", {})])
    # query vector closely matches item "a"
    provider.push(make_embedding_response([[0.9, 0.1, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]]))
    results = await svc.similarity_search_query("some query", top_k=2)
    assert results[0].id == "a"


@pytest.mark.asyncio
async def test_delete_from_index_removes_records_and_vectors(repos, scripted_ai_core):
    ai_core, provider = scripted_ai_core
    svc = VectorPlatformService(repos, ai_core)
    await svc.embed_and_index(workspace_id="ws-1", source_type="document_chunk", items=[("c1", "content", {})])
    deleted_count = await svc.delete_from_index("document_chunk", ["c1"])
    assert deleted_count == 1
    remaining = await repos.embedding_records.list_for_sources("document_chunk", ["c1"])
    assert remaining == []


@pytest.mark.asyncio
async def test_index_health_reports_dimension_consistency(repos, scripted_ai_core):
    ai_core, provider = scripted_ai_core
    svc = VectorPlatformService(repos, ai_core)
    empty_health = await svc.index_health("empty-index")
    assert empty_health.record_count == 0
    assert not empty_health.healthy

    await svc.embed_and_index(workspace_id="ws-1", source_type="document_chunk", items=[("c1", "content one", {})])
    healthy = await svc.index_health("default")
    assert healthy.record_count == 1
    assert healthy.healthy


@pytest.mark.asyncio
async def test_list_indexes_returns_distinct_index_names(repos, scripted_ai_core):
    ai_core, provider = scripted_ai_core
    svc = VectorPlatformService(repos, ai_core)
    await svc.embed_and_index(workspace_id="ws-1", source_type="document_chunk", items=[("c1", "content", {})], vector_store_index="chunks")
    await svc.embed_and_index(workspace_id="ws-1", source_type="memory_entry", items=[("m1", "content", {})], vector_store_index="memories")
    indexes = await svc.list_indexes("ws-1")
    assert set(indexes) == {"chunks", "memories"}
