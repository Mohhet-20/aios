from __future__ import annotations

from datetime import timedelta

import pytest

from observability_platform.core.exceptions import PermissionDeniedError, ValidationError
from observability_platform.database.base import utcnow
from observability_platform.domain.enums import ObservabilityRole
from observability_platform.governance.audit_service import AuditService
from observability_platform.governance.permission_service import PermissionService
from observability_platform.governance.retention_service import RetentionOrchestrationService
from observability_platform.models.governance import AuditLogEntryModel, RetentionPolicyModel
from observability_platform.models.logs import LogEntryModel
from observability_platform.models.metrics import MetricPointModel
from observability_platform.models.tracing import SpanModel, TraceModel


@pytest.mark.asyncio
async def test_grant_rejects_unknown_role(repos):
    svc = PermissionService(repos)
    with pytest.raises(ValidationError):
        await svc.grant("t1", "user-1", "not-a-role")


@pytest.mark.asyncio
async def test_effective_role_with_no_grants_is_none(repos):
    svc = PermissionService(repos)
    role = await svc.effective_role("t1", "user-1")
    assert role is None


@pytest.mark.asyncio
async def test_component_scoped_grant_overrides_tenant_wide(repos):
    svc = PermissionService(repos)
    await svc.grant("t1", "user-1", "viewer")
    await svc.grant("t1", "user-1", "admin", component_id="comp-a")

    tenant_wide = await svc.effective_role("t1", "user-1")
    assert tenant_wide == ObservabilityRole.VIEWER

    scoped = await svc.effective_role("t1", "user-1", component_id="comp-a")
    assert scoped == ObservabilityRole.ADMIN

    other_component = await svc.effective_role("t1", "user-1", component_id="comp-b")
    assert other_component == ObservabilityRole.VIEWER  # falls back to tenant-wide grant


@pytest.mark.asyncio
async def test_require_role_raises_when_insufficient(repos):
    svc = PermissionService(repos)
    await svc.grant("t1", "user-1", "viewer")
    with pytest.raises(PermissionDeniedError):
        await svc.require_role("t1", "user-1", ObservabilityRole.ADMIN)
    await svc.require_role("t1", "user-1", ObservabilityRole.VIEWER)  # should not raise


@pytest.mark.asyncio
async def test_audit_record_and_sweep(repos):
    svc = AuditService(repos)
    await svc.record("t1", actor_id="user-1", action="alert.acknowledge", resource_type="alert", resource_id="a1")
    old_entry = AuditLogEntryModel(
        tenant_id="t1", actor_id="user-1", action="old.action", resource_type="alert",
        occurred_at=utcnow() - timedelta(days=1000),
    )
    await repos.audit_log_entries.add(old_entry)

    recent = await svc.list_recent("t1")
    assert len(recent) == 2

    deleted = await svc.sweep_expired("t1")
    assert deleted == 1
    remaining = await svc.list_recent("t1")
    assert len(remaining) == 1


@pytest.mark.asyncio
async def test_retention_orchestrator_sweeps_everything(repos):
    now = utcnow()
    old = now - timedelta(days=1000)

    await repos.log_entries.add(LogEntryModel(
        tenant_id="t1", service_name="api", level="info", message="old", context={}, tags={}, event_time=old
    ))
    await repos.metric_points.add(MetricPointModel(
        tenant_id="t1", metric_name="x", metric_type="gauge", value=1.0, labels={}, timestamp=old
    ))
    trace = TraceModel(tenant_id="t1", trace_id="old-trace", started_at=old)
    await repos.traces.add(trace)
    await repos.spans.add(SpanModel(
        tenant_id="t1", trace_id="old-trace", span_id="s1", service_name="api", operation_name="op", start_time=old
    ))
    await repos.audit_log_entries.add(AuditLogEntryModel(
        tenant_id="t1", actor_id="user-1", action="old", resource_type="alert", occurred_at=old
    ))

    orchestrator = RetentionOrchestrationService(repos)
    result = await orchestrator.sweep_all("t1")
    assert result["logs_deleted"] == 1
    assert result["metric_points_deleted"] == 1
    assert result["spans_deleted"] == 1
    assert result["traces_deleted"] == 1
    assert result["audit_entries_deleted"] == 1


@pytest.mark.asyncio
async def test_retention_orchestrator_respects_per_resource_policy_override(repos):
    now = utcnow()
    recent_but_old_by_default = now - timedelta(days=45)
    await repos.metric_points.add(MetricPointModel(
        tenant_id="t1", metric_name="x", metric_type="gauge", value=1.0, labels={}, timestamp=recent_but_old_by_default
    ))
    await repos.retention_policies.add(RetentionPolicyModel(tenant_id="t1", resource_type="metrics", retention_days=90, is_enabled=True))

    orchestrator = RetentionOrchestrationService(repos)
    result = await orchestrator.sweep_all("t1")
    assert result["metric_points_deleted"] == 0  # 45 days old, within the 90-day custom policy
