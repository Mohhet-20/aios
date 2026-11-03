import pytest


@pytest.mark.asyncio
async def test_record_and_list_for_resource(audit_service):
    await audit_service.record("user-1", action="evaluation.publish", resource_type="evaluation", resource_id="eval-1", after={"status": "active"})
    await audit_service.record("user-1", action="evaluation.archive", resource_type="evaluation", resource_id="eval-1", before={"status": "active"}, after={"status": "archived"})
    await audit_service.record("user-2", action="dataset.publish", resource_type="dataset", resource_id="ds-1")

    entries = await audit_service.list_for_resource("evaluation", "eval-1")
    assert len(entries) == 2
    assert entries[0].action in {"evaluation.publish", "evaluation.archive"}


@pytest.mark.asyncio
async def test_list_for_actor(audit_service):
    await audit_service.record("user-1", action="evaluation.publish", resource_type="evaluation", resource_id="eval-1")
    await audit_service.record("user-2", action="dataset.publish", resource_type="dataset", resource_id="ds-1")

    entries = await audit_service.list_for_actor("user-1")
    assert len(entries) == 1
    assert entries[0].actor_id == "user-1"
