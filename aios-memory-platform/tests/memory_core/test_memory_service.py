import pytest

from memory_platform.core.exceptions import InvalidTransitionError, ValidationError
from memory_platform.domain.enums import MemoryStatus, MemoryType
from memory_platform.memory_core.memory_service import MemoryService
from memory_platform.memory_core.working_memory_service import WorkingMemoryService
from memory_platform.memory_registry.seed_types import BUILTIN_MEMORY_TYPE_POLICIES, seed_builtin_memory_types
from memory_platform.models.workspace import WorkspaceModel


async def _workspace(repos):
    ws = await repos.workspaces.add(WorkspaceModel(id="ws-1", name="Acme", slug="acme", organization_id="org-1"))
    return ws


@pytest.mark.asyncio
async def test_seed_builtin_memory_types_creates_all_16(repos):
    created = await seed_builtin_memory_types(repos)
    assert len(created) == 16
    assert {p.key for p in created} == {spec["key"] for spec in BUILTIN_MEMORY_TYPE_POLICIES}
    # idempotent
    again = await seed_builtin_memory_types(repos)
    assert len(again) == 16


@pytest.mark.asyncio
async def test_create_applies_policy_defaults(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = MemoryService(repos)
    entry = await svc.create(
        workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="The sky is blue.",
    )
    assert entry.importance_score == 0.7  # SEMANTIC default
    assert entry.status == MemoryStatus.ACTIVE.value
    assert entry.expires_at is None  # SEMANTIC has no retention window


@pytest.mark.asyncio
async def test_create_sets_expiry_from_retention_policy(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = MemoryService(repos)
    entry = await svc.create(
        workspace_id="ws-1", memory_type=MemoryType.SHORT_TERM, scope_type="user", scope_id="u-1", content="temp fact",
    )
    assert entry.expires_at is not None


@pytest.mark.asyncio
async def test_create_rejects_empty_content(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = MemoryService(repos)
    with pytest.raises(ValidationError):
        await svc.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="   ")


@pytest.mark.asyncio
async def test_get_records_access_and_bumps_importance(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = MemoryService(repos)
    entry = await svc.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="fact")
    before = entry.importance_score
    fetched = await svc.get(entry.id)
    assert fetched.access_count == 1
    assert fetched.importance_score > before
    assert fetched.last_accessed_at is not None


@pytest.mark.asyncio
async def test_get_without_record_access_does_not_bump(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = MemoryService(repos)
    entry = await svc.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="fact")
    fetched = await svc.get(entry.id, record_access=False)
    assert fetched.access_count == 0


@pytest.mark.asyncio
async def test_update_content_bumps_version_and_clears_summary(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = MemoryService(repos)
    entry = await svc.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="v1")
    await svc.summarize(entry.id, "a summary")
    updated = await svc.update_content(entry.id, "v2")
    assert updated.content == "v2"
    assert updated.version == 2
    assert updated.summary is None


@pytest.mark.asyncio
async def test_archive_restore_expire_lifecycle(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = MemoryService(repos)
    entry = await svc.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="fact")
    archived = await svc.archive(entry.id)
    assert archived.status == MemoryStatus.ARCHIVED.value
    restored = await svc.restore(entry.id)
    assert restored.status == MemoryStatus.ACTIVE.value
    expired = await svc.expire(entry.id)
    assert expired.status == MemoryStatus.EXPIRED.value
    with pytest.raises(InvalidTransitionError):
        await svc.restore(entry.id)  # can't restore from EXPIRED


@pytest.mark.asyncio
async def test_delete_soft_by_default(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = MemoryService(repos)
    entry = await svc.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="fact")
    await svc.delete(entry.id)
    reloaded = await repos.memory_entries.get_or_404(entry.id)
    assert reloaded.status == MemoryStatus.DELETED.value


@pytest.mark.asyncio
async def test_supersede_marks_old_and_creates_new(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = MemoryService(repos)
    old = await svc.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="Paris is the capital of France.")
    new = await svc.supersede(old.id, content="Paris is the capital of France, population 2.1M.")
    reloaded_old = await repos.memory_entries.get_or_404(old.id)
    assert reloaded_old.status == MemoryStatus.SUPERSEDED.value
    assert reloaded_old.superseded_by_id == new.id
    assert new.content.endswith("2.1M.")


@pytest.mark.asyncio
async def test_decayed_importance_uses_policy_decay_rate(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = MemoryService(repos)
    entry = await svc.create(workspace_id="ws-1", memory_type=MemoryType.WORKING, scope_type="session", scope_id="s-1", content="focus")
    accessed = await svc.get(entry.id)  # sets last_accessed_at, the decay anchor
    import datetime as dt
    future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=10)
    decayed = await svc.decayed_importance(entry.id, as_of=future)
    assert decayed < accessed.importance_score  # WORKING has a fast decay_rate=0.5, and time has passed since last access


@pytest.mark.asyncio
async def test_apply_retention_policies_expires_past_window(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = MemoryService(repos)
    entry = await svc.create(workspace_id="ws-1", memory_type=MemoryType.SHORT_TERM, scope_type="user", scope_id="u-1", content="temp")
    import datetime as dt
    far_future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(days=30)
    result = await svc.apply_retention_policies("ws-1", as_of=far_future)
    assert entry.id in result["expired_ids"]
    reloaded = await repos.memory_entries.get_or_404(entry.id)
    assert reloaded.status == MemoryStatus.EXPIRED.value


@pytest.mark.asyncio
async def test_audit_history_records_lifecycle_events(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = MemoryService(repos)
    entry = await svc.create(workspace_id="ws-1", memory_type=MemoryType.SEMANTIC, scope_type="user", scope_id="u-1", content="fact")
    await svc.update_content(entry.id, "fact v2")
    await svc.archive(entry.id)
    history = await svc.audit_history(entry.id)
    actions = {h.action for h in history}
    assert {"memory.create", "memory.update", "memory.archive"} <= actions


@pytest.mark.asyncio
async def test_maybe_compress_triggers_llm_summary_over_threshold(repos, scripted_ai_core):
    from tests.conftest import make_response
    ai_core, provider = scripted_ai_core
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = MemoryService(repos, ai_core=ai_core)
    long_content = "word " * 5000  # well over CONVERSATION's 4000-token threshold
    entry = await svc.create(workspace_id="ws-1", memory_type=MemoryType.CONVERSATION, scope_type="user", scope_id="u-1", content=long_content)
    provider.push(make_response("Concise running summary."))
    compressed = await svc.maybe_compress(entry.id)
    assert compressed.summary == "Concise running summary."


@pytest.mark.asyncio
async def test_maybe_compress_noop_under_threshold(repos, scripted_ai_core):
    ai_core, provider = scripted_ai_core
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = MemoryService(repos, ai_core=ai_core)
    entry = await svc.create(workspace_id="ws-1", memory_type=MemoryType.CONVERSATION, scope_type="user", scope_id="u-1", content="short turn")
    result = await svc.maybe_compress(entry.id)
    assert result.summary is None
    assert provider.calls == 0


@pytest.mark.asyncio
async def test_working_memory_max_entries_per_scope_archives_prior(repos):
    await seed_builtin_memory_types(repos)
    await _workspace(repos)
    svc = MemoryService(repos)
    working = WorkingMemoryService(repos, svc)
    first = await working.set_focus(workspace_id="ws-1", session_id="sess-1", content="focus A")
    second = await working.set_focus(workspace_id="ws-1", session_id="sess-1", content="focus B")
    reloaded_first = await repos.memory_entries.get_or_404(first.id)
    assert reloaded_first.status == MemoryStatus.ARCHIVED.value
    current = await working.get_focus("ws-1", "sess-1")
    assert current.id == second.id
    await working.clear_focus("ws-1", "sess-1")
    assert await working.get_focus("ws-1", "sess-1") is None
