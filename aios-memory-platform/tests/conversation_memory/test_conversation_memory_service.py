import pytest

from memory_platform.conversation_memory.conversation_memory_service import ConversationMemoryService
from memory_platform.memory_core.memory_service import MemoryService
from memory_platform.memory_registry.seed_types import seed_builtin_memory_types
from memory_platform.models.workspace import WorkspaceModel


async def _workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(id="ws-1", name="Acme", slug="acme", organization_id="org-1"))


@pytest.mark.asyncio
async def test_append_turn_orders_by_turn_index(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = ConversationMemoryService(repos, MemoryService(repos))
    await svc.append_turn(workspace_id="ws-1", conversation_id="conv-1", scope_type="user", scope_id="u-1", role="user", content="Hi")
    await svc.append_turn(workspace_id="ws-1", conversation_id="conv-1", scope_type="user", scope_id="u-1", role="assistant", content="Hello!")
    transcript = await svc.get_transcript("conv-1")
    assert [t.turn_index for t in transcript] == [0, 1]
    assert transcript[0].structured_content["role"] == "user"


@pytest.mark.asyncio
async def test_summarize_if_long_below_threshold_returns_none(repos, scripted_ai_core):
    ai_core, provider = scripted_ai_core
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = ConversationMemoryService(repos, MemoryService(repos), ai_core=ai_core)
    await svc.append_turn(workspace_id="ws-1", conversation_id="conv-1", scope_type="user", scope_id="u-1", role="user", content="short")
    result = await svc.summarize_if_long("conv-1")
    assert result is None
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_summarize_if_long_above_threshold_calls_llm(repos, scripted_ai_core):
    from tests.conftest import make_response
    ai_core, provider = scripted_ai_core
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = ConversationMemoryService(repos, MemoryService(repos), ai_core=ai_core)
    long_turn = "word " * 5000
    await svc.append_turn(workspace_id="ws-1", conversation_id="conv-1", scope_type="user", scope_id="u-1", role="user", content=long_turn)
    provider.push(make_response("Running summary of the conversation."))
    result = await svc.summarize_if_long("conv-1")
    assert result == "Running summary of the conversation."
