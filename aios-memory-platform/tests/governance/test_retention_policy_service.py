import datetime as dt

import pytest

from memory_platform.domain.enums import MemoryType, MemoryStatus, RetentionAction
from memory_platform.governance.retention_policy_service import RetentionPolicyService
from memory_platform.memory_core.memory_service import MemoryService
from memory_platform.memory_registry.seed_types import seed_builtin_memory_types
from memory_platform.models.workspace import WorkspaceModel


async def _workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(id="ws-1", name="Acme", slug="acme", organization_id="org-1"))


@pytest.mark.asyncio
async def test_create_and_list_policies(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    svc = RetentionPolicyService(repos, mem)
    await svc.create_policy(workspace_id="ws-1", retention_days=30, action_on_expiry=RetentionAction.ARCHIVE, memory_type=MemoryType.SESSION.value)
    policies = await svc.list_policies("ws-1")
    assert len(policies) == 1
    assert policies[0].retention_days == 30


@pytest.mark.asyncio
async def test_apply_workspace_retention_archives_old_entries(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    svc = RetentionPolicyService(repos, mem)
    await svc.create_policy(workspace_id="ws-1", retention_days=30, action_on_expiry=RetentionAction.ARCHIVE, memory_type=MemoryType.SESSION.value)

    entry = await mem.create(workspace_id="ws-1", memory_type=MemoryType.SESSION, scope_type="user", scope_id="u-1", content="old session note")
    far_future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=60)
    result = await svc.apply_workspace_retention_policies("ws-1", as_of=far_future)
    assert result["entries_archived"] == 1

    reloaded = await repos.memory_entries.get_or_404(entry.id)
    assert reloaded.status == MemoryStatus.ARCHIVED.value


@pytest.mark.asyncio
async def test_apply_workspace_retention_deletes_old_entries(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    svc = RetentionPolicyService(repos, mem)
    await svc.create_policy(workspace_id="ws-1", retention_days=1, action_on_expiry=RetentionAction.DELETE, scope_type="session")

    entry = await mem.create(workspace_id="ws-1", memory_type=MemoryType.EXECUTION, scope_type="session", scope_id="s-1", content="stale execution log")
    far_future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=5)
    result = await svc.apply_workspace_retention_policies("ws-1", as_of=far_future)
    assert result["entries_deleted"] == 1

    reloaded = await repos.memory_entries.get_or_404(entry.id)
    assert reloaded.status == MemoryStatus.DELETED.value


@pytest.mark.asyncio
async def test_apply_workspace_retention_ignores_recent_entries(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    svc = RetentionPolicyService(repos, mem)
    await svc.create_policy(workspace_id="ws-1", retention_days=365, action_on_expiry=RetentionAction.ARCHIVE, memory_type=MemoryType.SESSION.value)
    await mem.create(workspace_id="ws-1", memory_type=MemoryType.SESSION, scope_type="user", scope_id="u-1", content="fresh session note")

    result = await svc.apply_workspace_retention_policies("ws-1")
    assert result["entries_archived"] == 0


@pytest.mark.asyncio
async def test_deactivate_policy_excludes_it_from_application(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    mem = MemoryService(repos)
    svc = RetentionPolicyService(repos, mem)
    policy = await svc.create_policy(workspace_id="ws-1", retention_days=1, action_on_expiry=RetentionAction.ARCHIVE, memory_type=MemoryType.SESSION.value)
    await svc.deactivate_policy(policy.id)
    policies = await svc.list_policies("ws-1")
    assert policies == []
