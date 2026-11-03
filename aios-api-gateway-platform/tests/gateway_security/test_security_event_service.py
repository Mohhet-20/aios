from __future__ import annotations

import pytest

from gateway_platform.gateway_security.security_event_service import SecurityEventService

TENANT = "sec-event-tenant"


@pytest.mark.asyncio
async def test_record_and_list_recent_events(repos):
    service = SecurityEventService(repos)
    await service.record_event(TENANT, event_type="ip_blocked", severity="high", source_ip="10.0.0.1")
    await service.record_event(TENANT, event_type="threat_detected", severity="critical")

    all_events = await service.list_recent(TENANT)
    assert len(all_events) == 2

    critical_only = await service.list_recent(TENANT, severity="critical")
    assert len(critical_only) == 1
    assert critical_only[0].event_type == "threat_detected"
