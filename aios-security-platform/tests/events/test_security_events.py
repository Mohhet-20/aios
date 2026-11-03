"""Tests for the Security Events feed: the ten per-category
convenience recorders, severity defaults, listing/filtering, counts,
and retention sweep."""
from __future__ import annotations

from datetime import timedelta

import pytest

from security_platform.config.settings import Settings
from security_platform.domain.entities import _now
from security_platform.domain.enums import SecurityEventSeverity, SecurityEventType
from security_platform.events.security_event_service import SecurityEventService
from security_platform.models.events import SecurityEventModel

TENANT = "tenant-events"


@pytest.mark.asyncio
async def test_record_authentication_severity_reflects_outcome(repos):
    service = SecurityEventService(repos)
    success = await service.record_authentication(TENANT, actor_id="user-1", success=True, description="Login succeeded")
    assert success.severity == SecurityEventSeverity.INFO.value
    failure = await service.record_authentication(TENANT, actor_id="user-1", success=False, description="Login failed")
    assert failure.severity == SecurityEventSeverity.MEDIUM.value
    assert failure.event_type == SecurityEventType.AUTHENTICATION.value


@pytest.mark.asyncio
async def test_record_secrets_access_denial_is_high_severity(repos):
    service = SecurityEventService(repos)
    denied = await service.record_secrets_access(TENANT, actor_id="user-2", description="Denied secret read", success=False)
    assert denied.severity == SecurityEventSeverity.HIGH.value
    assert denied.event_type == SecurityEventType.SECRETS_ACCESS.value


@pytest.mark.asyncio
async def test_record_policy_prompt_tool_workflow_violations(repos):
    service = SecurityEventService(repos)
    policy = await service.record_policy_violation(TENANT, actor_id="user-3", description="Blocked by DLP policy")
    prompt = await service.record_prompt_violation(TENANT, actor_id="user-3", description="Jailbreak attempt")
    tool = await service.record_tool_violation(TENANT, actor_id="user-3", description="Unauthorized tool call")
    workflow = await service.record_workflow_violation(TENANT, actor_id="user-3", description="Suspicious workflow")
    assert {policy.event_type, prompt.event_type, tool.event_type, workflow.event_type} == {
        SecurityEventType.POLICY_VIOLATION.value, SecurityEventType.PROMPT_VIOLATION.value,
        SecurityEventType.TOOL_VIOLATION.value, SecurityEventType.WORKFLOW_VIOLATION.value,
    }


@pytest.mark.asyncio
async def test_list_recent_filters_by_type_and_severity(repos):
    service = SecurityEventService(repos)
    await service.record_authentication(TENANT, actor_id="user-4", success=True, description="ok")
    await service.record_authentication(TENANT, actor_id="user-4", success=False, description="bad")
    only_failures = await service.list_recent(TENANT, event_type=SecurityEventType.AUTHENTICATION.value, severity=SecurityEventSeverity.MEDIUM.value)
    assert len(only_failures) == 1
    assert only_failures[0].description == "bad"


@pytest.mark.asyncio
async def test_counts_by_type(repos):
    service = SecurityEventService(repos)
    await service.record_administrative_action(TENANT, actor_id="admin-1", description="Rotated key")
    await service.record_administrative_action(TENANT, actor_id="admin-1", description="Updated policy")
    counts = await service.counts_by_type(TENANT)
    assert counts.get(SecurityEventType.ADMINISTRATIVE_ACTION.value) == 2


@pytest.mark.asyncio
async def test_sweep_retention_deletes_old_events_only(repos):
    old_event = SecurityEventModel(
        tenant_id=TENANT, event_type=SecurityEventType.THREAT_DETECTION.value, severity="high",
        description="Old event", occurred_at=_now() - timedelta(days=10),
    )
    await repos.security_events.add(old_event)
    service = SecurityEventService(repos, settings=Settings(security_event_retention_days=1))
    await service.record_threat_detection(TENANT, entity_type="user", entity_id="user-5", description="Recent event")

    deleted_count = await service.sweep_retention(TENANT)
    assert deleted_count == 1
    remaining = await service.list_recent(TENANT)
    assert all(e.description != "Old event" for e in remaining)
