"""One smoke test per aggregate root, exercised through the real schema
— catches import errors, column typos, and FK-shape mistakes across
the whole 26-table schema in one fast pass."""
from __future__ import annotations

import pytest

from observability_platform.models.alerts import (
    AlertEscalationModel,
    AlertModel,
    AlertNotificationModel,
    AlertRuleModel,
    EscalationPolicyModel,
    MaintenanceWindowModel,
    NotificationChannelModel,
)
from observability_platform.models.capacity import CapacityForecastModel, CapacitySnapshotModel
from observability_platform.models.components import ComponentModel
from observability_platform.models.dashboards import DashboardModel
from observability_platform.models.governance import AccessGrantModel, AuditLogEntryModel, RetentionPolicyModel
from observability_platform.models.health import HealthCheckResultModel
from observability_platform.models.incidents import IncidentModel, IncidentPostmortemModel, IncidentTimelineEventModel
from observability_platform.models.logs import LogEntryModel
from observability_platform.models.metrics import MetricDefinitionModel, MetricPointModel
from observability_platform.models.reporting import ReportModel
from observability_platform.models.topology import TopologyEdgeModel, TopologyNodeModel
from observability_platform.models.tracing import SpanModel, TraceModel


@pytest.mark.asyncio
async def test_repository_smoke_all_aggregates(repos):
    component = await repos.components.add(
        ComponentModel(tenant_id="t1", name="api-gateway", component_type="api_gateway")
    )
    await repos.log_entries.add(
        LogEntryModel(tenant_id="t1", service_name="api-gateway", level="info", message="hello", context={}, tags={})
    )
    await repos.metric_definitions.add(
        MetricDefinitionModel(tenant_id="t1", name="cpu_usage", metric_type="gauge", unit="percent")
    )
    await repos.metric_points.add(
        MetricPointModel(tenant_id="t1", metric_name="cpu_usage", metric_type="gauge", value=42.0, labels={})
    )
    await repos.traces.add(TraceModel(tenant_id="t1", trace_id="trace-1", root_service="api-gateway"))
    await repos.spans.add(
        SpanModel(tenant_id="t1", trace_id="trace-1", span_id="span-1", service_name="api-gateway", operation_name="GET /x")
    )
    await repos.health_check_results.add(
        HealthCheckResultModel(tenant_id="t1", component_id=component.id, status="healthy")
    )
    rule = await repos.alert_rules.add(
        AlertRuleModel(tenant_id="t1", name="high-cpu", alert_type="threshold", condition={"gt": 90})
    )
    alert = await repos.alerts.add(
        AlertModel(tenant_id="t1", rule_id=rule.id, alert_type="threshold", title="High CPU", dedup_key="cpu-high-x")
    )
    policy = await repos.escalation_policies.add(EscalationPolicyModel(tenant_id="t1", name="default", levels=[]))
    await repos.alert_escalations.add(
        AlertEscalationModel(tenant_id="t1", alert_id=alert.id, policy_id=policy.id, level=1, target="oncall")
    )
    await repos.maintenance_windows.add(
        MaintenanceWindowModel(
            tenant_id="t1", name="db upgrade", starts_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            ends_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        )
    )
    channel = await repos.notification_channels.add(
        NotificationChannelModel(tenant_id="t1", name="oncall-email", channel_type="email", config={})
    )
    await repos.alert_notifications.add(
        AlertNotificationModel(tenant_id="t1", alert_id=alert.id, channel_id=channel.id)
    )
    incident = await repos.incidents.add(IncidentModel(tenant_id="t1", title="Outage", alert_id=alert.id))
    await repos.incident_timeline_events.add(
        IncidentTimelineEventModel(tenant_id="t1", incident_id=incident.id, event_type="created", message="opened")
    )
    await repos.incident_postmortems.add(
        IncidentPostmortemModel(tenant_id="t1", incident_id=incident.id, summary="root cause found")
    )
    await repos.capacity_snapshots.add(
        CapacitySnapshotModel(tenant_id="t1", resource_type="storage", value=100.0)
    )
    await repos.capacity_forecasts.add(
        CapacityForecastModel(tenant_id="t1", resource_type="storage", horizon_days=90, points=[])
    )
    node_a = await repos.topology_nodes.add(TopologyNodeModel(tenant_id="t1", name="api-gateway", node_type="service"))
    node_b = await repos.topology_nodes.add(TopologyNodeModel(tenant_id="t1", name="database", node_type="service"))
    await repos.topology_edges.add(
        TopologyEdgeModel(tenant_id="t1", source_node_id=node_a.id, target_node_id=node_b.id, edge_type="service")
    )
    await repos.dashboards.add(DashboardModel(tenant_id="t1", name="Ops", dashboard_type="operations"))
    await repos.reports.add(ReportModel(tenant_id="t1", report_type="availability", title="Weekly availability"))
    await repos.access_grants.add(AccessGrantModel(tenant_id="t1", principal_id="user-1", role="admin"))
    await repos.audit_log_entries.add(
        AuditLogEntryModel(tenant_id="t1", actor_id="user-1", action="alert.create", resource_type="alert")
    )
    await repos.retention_policies.add(RetentionPolicyModel(tenant_id="t1", resource_type="logs", retention_days=30))

    assert component.id is not None
    assert alert.dedup_key == "cpu-high-x"
    assert incident.title == "Outage"
