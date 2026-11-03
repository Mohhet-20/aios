import pytest

from docs_platform.collaboration.audit_service import AuditLogService

pytestmark = pytest.mark.asyncio

TENANT = "t-collab"


async def test_log_action_and_list_for_target(repos):
    svc = AuditLogService(repos)
    await svc.log_action(TENANT, actor_id="u1", action="page.published", target_ref="page:99")
    await svc.log_action(TENANT, actor_id="u1", action="page.archived", target_ref="page:99")
    await svc.log_action(TENANT, actor_id="u1", action="page.published", target_ref="page:other")

    entries = await svc.list_for_target(TENANT, "page:99")
    assert len(entries) == 2

    recent = await svc.list_recent(TENANT)
    assert len(recent) >= 3
