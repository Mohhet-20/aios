import datetime as dt

import pytest

from memory_platform.episodic_memory.episodic_memory_service import EpisodicMemoryService
from memory_platform.memory_core.memory_service import MemoryService
from memory_platform.memory_registry.seed_types import seed_builtin_memory_types
from memory_platform.models.workspace import WorkspaceModel


async def _workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(id="ws-1", name="Acme", slug="acme", organization_id="org-1"))


@pytest.mark.asyncio
async def test_record_event_and_query_by_time_range(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = EpisodicMemoryService(repos, MemoryService(repos))
    t0 = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    t1 = dt.datetime(2026, 2, 1, tzinfo=dt.timezone.utc)
    t2 = dt.datetime(2026, 6, 1, tzinfo=dt.timezone.utc)
    await svc.record_event(workspace_id="ws-1", scope_type="agent", scope_id="a-1", description="deployed v1", occurred_at=t0)
    await svc.record_event(workspace_id="ws-1", scope_type="agent", scope_id="a-1", description="deployed v2", occurred_at=t1)
    await svc.record_event(workspace_id="ws-1", scope_type="agent", scope_id="a-1", description="deployed v3 (out of range)", occurred_at=t2)

    results = await svc.query_by_time_range("ws-1", "agent", "a-1", start=t0, end=t1)
    assert len(results) == 2
    assert [r.content for r in results] == ["deployed v1", "deployed v2"]
