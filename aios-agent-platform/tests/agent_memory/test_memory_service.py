import pytest

from agent_platform.agent_memory.memory_service import MemoryService
from agent_platform.agent_registry.agent_service import AgentService
from agent_platform.agent_registry.type_service import AgentTypeService
from agent_platform.core.exceptions import AuthorizationError
from agent_platform.models.workspace import WorkspaceModel


async def _seed_workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="WS", slug="ws-mem", organization_id="org1"))


async def _seed_agent(repos, ws_id, *, memory_access: dict | None = None):
    type_svc = AgentTypeService(repos)
    await type_svc.seed_builtin_types()
    agent_type = await type_svc.get_by_key("memory")
    agent_svc = AgentService(repos)
    return await agent_svc.create_agent(ws_id, agent_type.id, name="Memory Agent", owner_id="u1", memory_access=memory_access)


@pytest.mark.asyncio
async def test_remember_and_recall_roundtrip(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, memory_access={"short_term": True})

    svc = MemoryService(repos)
    await svc.remember(agent.id, "favorite_color", "blue")
    assert await svc.recall(agent.id, "favorite_color") == "blue"


@pytest.mark.asyncio
async def test_access_denied_without_grant(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, memory_access={})

    svc = MemoryService(repos)
    with pytest.raises(AuthorizationError):
        await svc.remember(agent.id, "k", "v")


@pytest.mark.asyncio
async def test_recent_returns_most_recently_written_first(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, memory_access={"short_term": True})

    svc = MemoryService(repos)
    await svc.remember(agent.id, "a", 1)
    await svc.remember(agent.id, "b", 2)
    await svc.remember(agent.id, "c", 3)

    recent = await svc.recent(agent.id, limit=2)
    assert [entry["key"] for entry in recent] == ["c", "b"]


@pytest.mark.asyncio
async def test_search_matches_by_substring(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, memory_access={"semantic": True})

    svc = MemoryService(repos)
    await svc.remember(agent.id, "note_1", "the sky is blue", kind="semantic")
    await svc.remember(agent.id, "note_2", "grass is green", kind="semantic")

    results = await svc.search(agent.id, "blue")
    assert len(results) == 1
    assert results[0]["key"] == "note_1"


@pytest.mark.asyncio
async def test_forget_removes_single_key_and_all_keys(repos, scripted_ai_core):
    ws = await _seed_workspace(repos)
    agent = await _seed_agent(repos, ws.id, memory_access={"short_term": True})

    svc = MemoryService(repos)
    await svc.remember(agent.id, "a", 1)
    await svc.remember(agent.id, "b", 2)

    await svc.forget(agent.id, "a")
    assert await svc.recall(agent.id, "a") is None
    assert await svc.recall(agent.id, "b") == 2

    await svc.forget(agent.id)
    assert await svc.recall(agent.id, "b") is None
