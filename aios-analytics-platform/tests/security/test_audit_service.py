from __future__ import annotations

import pytest

from analytics_platform.core.exceptions import ValidationError
from analytics_platform.security.audit_service import AuditLogService

TENANT = "audit-tenant"


@pytest.mark.asyncio
async def test_record_rejects_bad_action_type(repos):
    service = AuditLogService(repos)
    with pytest.raises(ValidationError):
        await service.record(TENANT, action_type="teleport", resource_type="dashboard")


@pytest.mark.asyncio
async def test_record_and_list_recent(repos):
    service = AuditLogService(repos)
    await service.record(TENANT, action_type="view", resource_type="dashboard", actor_id="user-1", resource_id="dash-1")
    await service.record(TENANT, action_type="export", resource_type="report", actor_id="user-1", resource_id="rep-1")

    all_entries = await service.list_recent(TENANT)
    assert len(all_entries) == 2

    exports_only = await service.list_recent(TENANT, action_type="export")
    assert len(exports_only) == 1
    assert exports_only[0].resource_type == "report"
