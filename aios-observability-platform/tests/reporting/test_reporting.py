from __future__ import annotations

from datetime import timedelta

import pytest

from observability_platform.core.exceptions import ValidationError
from observability_platform.database.base import utcnow
from observability_platform.health.healthcheck_service import HealthCheckService
from observability_platform.incidents.incident_service import IncidentService
from observability_platform.logs.ingest_service import LogIngestService
from observability_platform.models.components import ComponentModel
from observability_platform.models.governance import RetentionPolicyModel
from observability_platform.reporting.report_service import ReportService


@pytest.mark.asyncio
async def test_generate_report_rejects_unknown_type(repos):
    svc = ReportService(repos)
    with pytest.raises(ValidationError):
        await svc.generate_report("t1", "not-a-type")


@pytest.mark.asyncio
async def test_availability_report_computes_uptime_pct(repos):
    component = await repos.components.add(ComponentModel(tenant_id="t1", name="api", component_type="api_gateway"))
    health_svc = HealthCheckService(repos)
    await health_svc.record_result("t1", component.id, status="healthy")
    await health_svc.record_result("t1", component.id, status="healthy")
    await health_svc.record_result("t1", component.id, status="unhealthy")

    report_svc = ReportService(repos)
    report = await report_svc.generate_report("t1", "availability")
    assert report.status == "ready"
    pct = report.result["availability_pct_by_component"]["api"]
    assert round(pct) == 67


@pytest.mark.asyncio
async def test_incident_report_computes_mttr(repos):
    incident_svc = IncidentService(repos)
    incident = await incident_svc.create_incident("t1", title="Outage", severity="sev2")
    await incident_svc.resolve("t1", incident.id)
    await incident_svc.close("t1", incident.id)

    report_svc = ReportService(repos)
    report = await report_svc.generate_report("t1", "incident")
    assert report.status == "ready"
    assert report.result["incident_count"] == 1
    assert report.result["mean_time_to_resolve_minutes"] is not None


@pytest.mark.asyncio
async def test_sla_report_computes_compliance_pct(repos):
    incident_svc = IncidentService(repos)
    incident = await incident_svc.create_incident("t1", title="Quick fix", severity="sev4")
    await incident_svc.resolve("t1", incident.id)
    await incident_svc.close("t1", incident.id)

    report_svc = ReportService(repos)
    report = await report_svc.generate_report("t1", "sla", params={"sla_minutes": 1440})
    assert report.result["compliance_pct"] == 100.0


@pytest.mark.asyncio
async def test_error_report_counts_by_level(repos):
    log_svc = LogIngestService(repos)
    await log_svc.ingest("t1", service_name="api", level="error", message="boom")
    await log_svc.ingest("t1", service_name="api", level="critical", message="fire")
    await log_svc.ingest("t1", service_name="api", level="info", message="fine")

    report_svc = ReportService(repos)
    report = await report_svc.generate_report("t1", "error")
    assert report.result["error_count"] == 2


@pytest.mark.asyncio
async def test_usage_report_counts_logs_and_metrics(repos):
    log_svc = LogIngestService(repos)
    await log_svc.ingest("t1", service_name="api", level="info", message="x")
    from observability_platform.metrics.ingest_service import MetricIngestService
    metric_svc = MetricIngestService(repos)
    await metric_svc.ingest("t1", name="report_usage_metric", metric_type="counter", value=1.0)

    report_svc = ReportService(repos)
    report = await report_svc.generate_report("t1", "usage")
    assert report.result["log_entries"] >= 1
    assert report.result["metric_points"] >= 1


@pytest.mark.asyncio
async def test_compliance_report_lists_retention_policies(repos):
    await repos.retention_policies.add(RetentionPolicyModel(tenant_id="t1", resource_type="logs", retention_days=30))
    report_svc = ReportService(repos)
    report = await report_svc.generate_report("t1", "compliance")
    assert len(report.result["retention_policies"]) == 1


@pytest.mark.asyncio
async def test_trend_report_compares_periods(repos):
    now = utcnow()
    from observability_platform.models.logs import LogEntryModel
    await repos.log_entries.add(LogEntryModel(
        tenant_id="t1", service_name="api", level="error", message="recent-error", context={}, tags={},
        event_time=now - timedelta(hours=1),
    ))
    await repos.log_entries.add(LogEntryModel(
        tenant_id="t1", service_name="api", level="error", message="older-error", context={}, tags={},
        event_time=now - timedelta(days=3),
    ))

    report_svc = ReportService(repos)
    report = await report_svc.generate_report("t1", "trend", period_start=now - timedelta(days=1), period_end=now)
    assert report.result["current_period_errors"] == 1
