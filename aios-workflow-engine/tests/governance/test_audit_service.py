"""AuditService: the shared record/query API over the single consolidated
AuditLogEntryModel table that ApprovalService and RBACService both write
through directly. Not exercised as its own unit test elsewhere — those
services' tests only assert audit side-effects incidentally."""
import pytest

from workflow_platform.security.audit_service import AuditService


@pytest.fixture
def audit_service(repos):
    return AuditService(repos)


@pytest.mark.asyncio
async def test_record_and_list_for_resource(audit_service):
    await audit_service.record("u1", "workflow_created", "workflow", "wf-1", after={"name": "Pipeline"})
    await audit_service.record("u2", "workflow_updated", "workflow", "wf-1", before={"name": "Pipeline"}, after={"name": "Pipeline 2"})
    await audit_service.record("u1", "workflow_created", "workflow", "wf-2", after={"name": "Other"})

    entries = await audit_service.list_for_resource("workflow", "wf-1")
    assert len(entries) == 2
    assert {e.action for e in entries} == {"workflow_created", "workflow_updated"}
    assert all(e.resource_id == "wf-1" for e in entries)


@pytest.mark.asyncio
async def test_list_for_actor(audit_service):
    await audit_service.record("u1", "grant", "workspace", "ws-1")
    await audit_service.record("u1", "revoke", "workspace", "ws-2")
    await audit_service.record("u2", "grant", "workspace", "ws-3")

    entries = await audit_service.list_for_actor("u1")
    assert len(entries) == 2
    assert all(e.actor_id == "u1" for e in entries)


@pytest.mark.asyncio
async def test_list_for_resource_respects_limit(audit_service):
    for i in range(10):
        await audit_service.record("u1", "action", "workflow", "wf-1", after={"i": i})

    entries = await audit_service.list_for_resource("workflow", "wf-1", limit=3)
    assert len(entries) == 3


@pytest.mark.asyncio
async def test_before_after_snapshots_are_preserved(audit_service):
    entry = await audit_service.record(
        "u1", "workflow_updated", "workflow", "wf-9",
        before={"status": "draft"}, after={"status": "active"},
    )
    assert entry.before == {"status": "draft"}
    assert entry.after == {"status": "active"}
