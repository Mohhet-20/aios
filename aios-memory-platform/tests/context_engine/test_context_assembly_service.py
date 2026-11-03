import pytest

from memory_platform.context_engine.context_assembly_service import ContextAssemblyService
from memory_platform.domain.enums import MemoryType
from memory_platform.memory_core.memory_service import MemoryService
from memory_platform.memory_registry.seed_types import seed_builtin_memory_types
from memory_platform.models.workspace import WorkspaceModel
from memory_platform.retrieval.retrieval_service import RetrievalService


async def _workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(id="ws-1", name="Acme", slug="acme", organization_id="org-1"))


@pytest.mark.asyncio
async def test_assemble_context_includes_matching_memories_with_citations(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="The deployment pipeline uses blue-green rollout.", title="Deployment Pipeline")

    retrieval = RetrievalService(repos)
    ctx = ContextAssemblyService(retrieval)
    result = await ctx.assemble_context("ws-1", "deployment pipeline")
    assert result.items_included == 1
    assert "blue-green rollout" in result.text
    assert len(result.citations) == 1
    assert result.citations[0].source_type == "memory_entry"
    assert result.citations[0].title == "Deployment Pipeline"
    assert "[1]" in result.text


@pytest.mark.asyncio
async def test_duplicate_removal_collapses_near_identical_content(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="Our support SLA is 24 hours for critical issues.")
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="Our support SLA is 24 hours for critical issues.")

    retrieval = RetrievalService(repos)
    ctx = ContextAssemblyService(retrieval)
    result = await ctx.assemble_context("ws-1", "critical issues")
    assert result.items_included == 1
    assert result.duplicates_removed == 1


@pytest.mark.asyncio
async def test_conflict_resolution_keeps_higher_importance_same_titled_fact(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    await mem.create(
        workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1",
        content="The on-call rotation is weekly, starting Mondays.", title="On-call Rotation", importance_score=0.3,
    )
    await mem.create(
        workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1",
        content="The on-call rotation is now bi-weekly, starting Mondays, updated policy.", title="On-call Rotation", importance_score=0.95,
    )

    retrieval = RetrievalService(repos)
    ctx = ContextAssemblyService(retrieval)
    result = await ctx.assemble_context("ws-1", "on-call rotation")
    assert result.conflicts_resolved == 1
    assert result.items_included == 1
    assert "bi-weekly" in result.text  # the higher-importance, more recent fact won


@pytest.mark.asyncio
async def test_token_budget_management_excludes_items_over_budget(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    for i in range(5):
        await mem.create(
            workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1",
            content=f"Budget test fact number {i}: " + ("word " * 100),
        )

    retrieval = RetrievalService(repos)
    ctx = ContextAssemblyService(retrieval)
    result = await ctx.assemble_context("ws-1", "budget test fact", token_budget=50, allow_llm_summarization=False)
    assert result.items_included < 5
    assert result.total_tokens <= 60  # small slack for the final partial fragment


@pytest.mark.asyncio
async def test_llm_summarization_triggers_when_over_budget(repos, scripted_ai_core):
    from tests.conftest import make_response

    ai_core, provider = scripted_ai_core
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    for i in range(4):
        await mem.create(
            workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1",
            content=f"Summarization test content block {i}: " + ("detail " * 80),
        )

    retrieval = RetrievalService(repos)
    ctx = ContextAssemblyService(retrieval, ai_core=ai_core)
    provider.push(make_response("A single condensed paragraph covering all the retrieved facts."))
    result = await ctx.assemble_context("ws-1", "summarization test content", token_budget=40, allow_llm_summarization=True)
    assert result.was_summarized is True
    assert result.text == "A single condensed paragraph covering all the retrieved facts."


@pytest.mark.asyncio
async def test_assemble_context_no_matches_returns_empty(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    retrieval = RetrievalService(repos)
    ctx = ContextAssemblyService(retrieval)
    result = await ctx.assemble_context("ws-1", "nothing will match this query at all")
    assert result.items_included == 0
    assert result.text == ""
    assert result.citations == []
