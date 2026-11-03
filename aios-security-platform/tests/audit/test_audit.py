"""Tests for the immutable Audit Platform: generic record(), resource
and actor history queries, and retention sweep."""
from __future__ import annotations

from datetime import timedelta

import pytest

from security_platform.audit.audit_service import AuditService
from security_platform.config.settings import Settings
from security_platform.domain.entities import _now
from security_platform.models.events import AuditLogEntryModel

TENANT = "tenant-audit"


@pytest.mark.asyncio
async def test_record_and_history_for_resource(repos):
    service = AuditService(repos)
    await service.record(TENANT, action="policy.created", resource_type="policy", resource_id="policy-1", actor_id="admin-1")
    await service.record(TENANT, action="policy.updated", resource_type="policy", resource_id="policy-1", actor_id="admin-1")
    await service.record(TENANT, action="policy.created", resource_type="policy", resource_id="policy-2", actor_id="admin-2")

    history = await service.history_for_resource(TENANT, "policy", "policy-1")
    assert len(history) == 2
    assert {h.action for h in history} == {"policy.created", "policy.updated"}


@pytest.mark.asyncio
async def test_history_for_actor(repos):
    service = AuditService(repos)
    await service.record(TENANT, action="approval.decided", resource_type="approval_request", resource_id="req-1", actor_id="approver-1")
    await service.record(TENANT, action="model.invoked", resource_type="model", resource_id="model-1", actor_id="approver-1")
    await service.record(TENANT, action="model.invoked", resource_type="model", resource_id="model-2", actor_id="someone-else")

    history = await service.history_for_actor(TENANT, "approver-1")
    assert len(history) == 2


@pytest.mark.asyncio
async def test_recent_returns_entries_for_tenant(repos):
    service = AuditService(repos)
    await service.record(TENANT, action="tool.invoked", resource_type="tool", resource_id="tool-1")
    recent = await service.recent(TENANT)
    assert len(recent) == 1


@pytest.mark.asyncio
async def test_sweep_retention_deletes_only_stale_entries(repos):
    stale = AuditLogEntryModel(
        tenant_id=TENANT, action="legacy.action", resource_type="legacy", occurred_at=_now() - timedelta(days=10)
    )
    await repos.audit_log_entries.add(stale)
    service = AuditService(repos, settings=Settings(audit_log_retention_days=1))
    await service.record(TENANT, action="fresh.action", resource_type="fresh")

    deleted = await service.sweep_retention(TENANT)
    assert deleted == 1
    remaining = await service.recent(TENANT)
    assert all(e.action != "legacy.action" for e in remaining)
