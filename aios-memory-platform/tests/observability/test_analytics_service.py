import pytest

from memory_platform.analytics.analytics_service import AnalyticsService
from memory_platform.context_engine.context_assembly_service import ContextAssemblyService
from memory_platform.domain.enums import DocumentStatus, DocumentType, MemoryType
from memory_platform.knowledge.knowledge_service import KnowledgeService
from memory_platform.memory_core.memory_service import MemoryService
from memory_platform.memory_registry.seed_types import seed_builtin_memory_types
from memory_platform.models.document import DocumentModel
from memory_platform.models.workspace import WorkspaceModel
from memory_platform.retrieval.retrieval_service import RetrievalService
from memory_platform.vector_store.vector_platform_service import VectorPlatformService
from memory_platform.database.base import new_uuid


async def _workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(id="ws-1", name="Acme", slug="acme", organization_id="org-1"))


@pytest.mark.asyncio
async def test_retrieval_performance_computed_from_real_logs(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="analytics test fact one")
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="unrelated content")

    retrieval = RetrievalService(repos)
    await retrieval.multi_stage_retrieve("ws-1", "analytics test fact", top_k=5)
    await retrieval.multi_stage_retrieve("ws-1", "nothing matches this at all", top_k=5)

    analytics = AnalyticsService(repos)
    perf = await analytics.retrieval_performance("ws-1")
    assert perf.total_queries == 2
    assert perf.failure_rate == 0.0
    assert perf.non_empty_result_rate == 0.5  # one query matched, one didn't
    assert perf.avg_latency_ms >= 0.0
    assert perf.p95_latency_ms >= perf.p50_latency_ms


@pytest.mark.asyncio
async def test_context_assembly_performance_from_real_logs(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="context assembly analytics fact")

    retrieval = RetrievalService(repos)
    ctx = ContextAssemblyService(retrieval)
    await ctx.assemble_context("ws-1", "context assembly analytics")

    analytics = AnalyticsService(repos)
    perf = await analytics.context_assembly_performance("ws-1")
    assert perf.total_assemblies == 1
    assert perf.avg_tokens_used > 0
    assert perf.compression_rate == 0.0


@pytest.mark.asyncio
async def test_embedding_performance_reports_index_health(repos, scripted_ai_core):
    ai_core, provider = scripted_ai_core
    await _workspace(repos)
    vp = VectorPlatformService(repos, ai_core)
    await vp.embed_and_index(workspace_id="ws-1", source_type="document_chunk", items=[("c1", "content one", {})], vector_store_index="chunks")

    analytics = AnalyticsService(repos)
    perf = await analytics.embedding_performance("ws-1")
    assert "chunks" in perf.indexes
    assert perf.indexes["chunks"]["record_count"] == 1
    assert perf.indexes["chunks"]["healthy"] is True


@pytest.mark.asyncio
async def test_memory_analytics_reads_and_writes(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    entry = await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="fact")
    await mem.get(entry.id)  # bumps access_count
    await mem.get(entry.id)

    analytics = AnalyticsService(repos)
    result = await analytics.memory_analytics("ws-1")
    assert result.total_reads == 2
    assert result.entries_created_in_window == 1


@pytest.mark.asyncio
async def test_knowledge_growth(repos):
    await _workspace(repos)
    ks = KnowledgeService(repos)
    kb = await ks.create_knowledge_base(workspace_id="ws-1", name="KB", slug="kb", owner_id="user-1")
    await ks.create_item(workspace_id="ws-1", knowledge_base_id=kb.id, title="Item A", content="content", owner_id="user-1")

    analytics = AnalyticsService(repos)
    growth = await analytics.knowledge_growth("ws-1")
    assert growth.total_items == 1
    assert growth.items_created_in_window == 1


@pytest.mark.asyncio
async def test_storage_usage(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="fact")
    await repos.documents.add(DocumentModel(
        id=new_uuid(), workspace_id="ws-1", title="Doc", document_type=DocumentType.TEXT.value, uploaded_by="user-1",
        status=DocumentStatus.PROCESSED.value, size_bytes=2048,
    ))

    analytics = AnalyticsService(repos)
    usage = await analytics.storage_usage("ws-1")
    assert usage.total_document_bytes == 2048
    assert usage.document_count == 1
    assert usage.memory_entry_count == 1


@pytest.mark.asyncio
async def test_agent_memory_usage_grouped_by_agent(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    e1 = await mem.create(workspace_id="ws-1", memory_type=MemoryType.AGENT, scope_type="agent", scope_id="agent-1", content="fact one")
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.AGENT, scope_type="agent", scope_id="agent-1", content="fact two")
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.AGENT, scope_type="agent", scope_id="agent-2", content="fact three")
    await mem.get(e1.id)

    analytics = AnalyticsService(repos)
    usage = await analytics.agent_memory_usage("ws-1")
    by_agent = {u.agent_id: u for u in usage}
    assert by_agent["agent-1"].entry_count == 2
    assert by_agent["agent-1"].total_access_count == 1
    assert by_agent["agent-2"].entry_count == 1
