import datetime as dt

import pytest

from memory_platform.domain.enums import MemoryType, SearchMode
from memory_platform.memory_core.memory_service import MemoryService
from memory_platform.memory_registry.seed_types import seed_builtin_memory_types
from memory_platform.models.workspace import WorkspaceModel
from memory_platform.retrieval.retrieval_service import RetrievalService
from memory_platform.vector_store.vector_platform_service import VectorPlatformService


async def _workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(id="ws-1", name="Acme", slug="acme", organization_id="org-1"))


@pytest.mark.asyncio
async def test_keyword_search_finds_matching_content(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="Paris is the capital of France")
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="Tokyo is the capital of Japan")
    retrieval = RetrievalService(repos)
    results = await retrieval.keyword_search("ws-1", "france")
    assert len(results) == 1
    assert "Paris" in results[0].content
    assert results[0].match_types == ["keyword"]


@pytest.mark.asyncio
async def test_semantic_search_ranks_by_vector_similarity(repos, scripted_ai_core):
    from tests.conftest import make_embedding_response

    ai_core, provider = scripted_ai_core
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    e1 = await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="cats are small pets")
    e2 = await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="stock market rose today")

    vp = VectorPlatformService(repos, ai_core)
    provider.push(make_embedding_response([[1.0, 0.0, 0, 0, 0, 0, 0, 0], [0.0, 1.0, 0, 0, 0, 0, 0, 0]]))
    await vp.embed_and_index(workspace_id="ws-1", source_type="memory_entry", items=[(e1.id, e1.content, {}), (e2.id, e2.content, {})])

    retrieval = RetrievalService(repos, vector_platform=vp)
    provider.push(make_embedding_response([[0.9, 0.1, 0, 0, 0, 0, 0, 0]]))
    results = await retrieval.semantic_search("ws-1", "small furry animal", top_k=2)
    assert results[0].id == e1.id
    assert results[0].match_types == ["semantic"]


@pytest.mark.asyncio
async def test_hybrid_search_merges_keyword_and_semantic_results(repos, scripted_ai_core):
    from tests.conftest import make_embedding_response

    ai_core, provider = scripted_ai_core
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    keyword_only = await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="unique keyword zzyzx appears here")
    semantic_only = await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="totally different phrasing")

    vp = VectorPlatformService(repos, ai_core)
    provider.push(make_embedding_response([[1.0, 0, 0, 0, 0, 0, 0, 0], [0.0, 1.0, 0, 0, 0, 0, 0, 0]]))
    await vp.embed_and_index(workspace_id="ws-1", source_type="memory_entry", items=[(keyword_only.id, keyword_only.content, {}), (semantic_only.id, semantic_only.content, {})])

    retrieval = RetrievalService(repos, vector_platform=vp)
    provider.push(make_embedding_response([[0.0, 1.0, 0, 0, 0, 0, 0, 0]]))  # closely matches semantic_only
    results = await retrieval.hybrid_search("ws-1", "zzyzx", top_k=5)
    ids = {r.id for r in results}
    assert keyword_only.id in ids
    assert semantic_only.id in ids


@pytest.mark.asyncio
async def test_agent_user_project_aware_search_filters_by_scope(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.AGENT, scope_type="agent", scope_id="agent-1", content="agent-1 remembers a deployment fact")
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.AGENT, scope_type="agent", scope_id="agent-2", content="agent-2 remembers a deployment fact")

    retrieval = RetrievalService(repos)
    results = await retrieval.agent_aware_search("ws-1", "agent-1", "deployment", mode=SearchMode.KEYWORD)
    assert len(results) == 1
    assert results[0].metadata["scope_id"] == "agent-1"


@pytest.mark.asyncio
async def test_time_aware_search_filters_by_created_at_range(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="time-bound searchable fact")

    retrieval = RetrievalService(repos)
    now = dt.datetime.now(dt.timezone.utc)
    in_range = await retrieval.time_aware_search("ws-1", "searchable", start=now - dt.timedelta(hours=1), end=now + dt.timedelta(hours=1), mode=SearchMode.KEYWORD)
    assert len(in_range) == 1

    out_of_range = await retrieval.time_aware_search("ws-1", "searchable", start=now - dt.timedelta(days=10), end=now - dt.timedelta(days=5), mode=SearchMode.KEYWORD)
    assert out_of_range == []


@pytest.mark.asyncio
async def test_multi_stage_retrieve_scopes_and_reranks(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.PROJECT, scope_type="project", scope_id="proj-1", content="deployment runbook for project alpha")
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.PROJECT, scope_type="project", scope_id="proj-2", content="deployment runbook for project beta")

    retrieval = RetrievalService(repos)
    results = await retrieval.multi_stage_retrieve("ws-1", "deployment runbook", scope_type="project", scope_id="proj-1", top_k=5)
    assert len(results) == 1
    assert results[0].metadata["scope_id"] == "proj-1"
    assert "rerank_score" in results[0].metadata


@pytest.mark.asyncio
async def test_multi_stage_retrieve_with_query_expansion(repos, scripted_ai_core):
    from tests.conftest import make_response

    ai_core, provider = scripted_ai_core
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="synonym-matchable expanded content")

    retrieval = RetrievalService(repos, ai_core=ai_core)
    import json
    provider.push(make_response(json.dumps({"expanded_queries": ["expanded content synonym"]})))
    results = await retrieval.multi_stage_retrieve("ws-1", "synonym-matchable expanded content", use_query_expansion=True, top_k=5)
    assert len(results) >= 1


def test_compress_content_truncates_long_text():
    long_text = "word " * 200
    compressed = RetrievalService.compress_content(long_text, max_chars=50)
    assert len(compressed) < len(long_text)
    assert compressed.endswith("…")


def test_compress_content_leaves_short_text_untouched():
    short = "a short string"
    assert RetrievalService.compress_content(short, max_chars=50) == short
