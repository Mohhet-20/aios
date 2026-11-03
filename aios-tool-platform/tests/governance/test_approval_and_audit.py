import pytest

from tool_platform.core.exceptions import ValidationError
from tool_platform.domain.enums import ApprovalStatus


@pytest.mark.asyncio
async def test_request_approve_creates_a_consumable_gate(approval_service):
    gate = await approval_service.request_approval("tool", "tool-1", requested_by="user-1", reason="needs review")
    assert gate.status == ApprovalStatus.PENDING.value

    approved = await approval_service.approve(gate.id, approver_id="admin-1", notes="looks fine")
    assert approved.status == ApprovalStatus.APPROVED.value
    assert approved.approver_id == "admin-1"
    assert approved.resolved_at is not None


@pytest.mark.asyncio
async def test_reject_sets_rejected_status(approval_service):
    gate = await approval_service.request_approval("tool", "tool-1", requested_by="user-1")
    rejected = await approval_service.reject(gate.id, approver_id="admin-1", notes="too risky")
    assert rejected.status == ApprovalStatus.REJECTED.value


@pytest.mark.asyncio
async def test_cannot_decide_an_already_decided_gate(approval_service):
    gate = await approval_service.request_approval("tool", "tool-1", requested_by="user-1")
    await approval_service.approve(gate.id, approver_id="admin-1")
    with pytest.raises(ValidationError):
        await approval_service.approve(gate.id, approver_id="admin-2")


@pytest.mark.asyncio
async def test_consume_succeeds_exactly_once(approval_service):
    gate = await approval_service.request_approval("tool", "tool-1", requested_by="user-1")
    await approval_service.approve(gate.id, approver_id="admin-1")

    consumed = await approval_service.consume(gate.id, resource_type="tool", resource_id="tool-1")
    assert consumed.consumed_at is not None

    with pytest.raises(ValidationError):
        await approval_service.consume(gate.id, resource_type="tool", resource_id="tool-1")


@pytest.mark.asyncio
async def test_consume_rejects_mismatched_resource(approval_service):
    gate = await approval_service.request_approval("tool", "tool-1", requested_by="user-1")
    await approval_service.approve(gate.id, approver_id="admin-1")
    with pytest.raises(ValidationError):
        await approval_service.consume(gate.id, resource_type="tool", resource_id="tool-2")


@pytest.mark.asyncio
async def test_consume_rejects_unapproved_gate(approval_service):
    gate = await approval_service.request_approval("tool", "tool-1", requested_by="user-1")
    with pytest.raises(ValidationError):
        await approval_service.consume(gate.id, resource_type="tool", resource_id="tool-1")


@pytest.mark.asyncio
async def test_list_pending_and_list_for_resource(approval_service):
    await approval_service.request_approval("tool", "tool-1", requested_by="user-1")
    gate2 = await approval_service.request_approval("tool", "tool-1", requested_by="user-2")
    await approval_service.approve(gate2.id, approver_id="admin-1")

    pending = await approval_service.list_pending(resource_type="tool")
    assert len(pending) == 1

    for_resource = await approval_service.list_for_resource("tool", "tool-1")
    assert len(for_resource) == 2


@pytest.mark.asyncio
async def test_audit_service_records_and_lists(audit_service):
    await audit_service.record("user-1", "tool.create", "tool", "tool-1", after={"name": "T"})
    await audit_service.record("user-1", "tool.update", "tool", "tool-1", before={"name": "T"}, after={"name": "T2"})
    await audit_service.record("user-2", "tool.execute", "tool", "tool-2")

    for_resource = await audit_service.list_for_resource("tool", "tool-1")
    assert len(for_resource) == 2
    assert for_resource[0].action in ("tool.create", "tool.update")

    for_actor = await audit_service.list_for_actor("user-1")
    assert len(for_actor) == 2

    for_actor_2 = await audit_service.list_for_actor("user-2")
    assert len(for_actor_2) == 1
