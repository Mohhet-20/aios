from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from analytics_platform.analytics.aggregation_engine import AggregationEngine
from analytics_platform.kpis.kpi_service import KpiService
from analytics_platform.kpis.snapshot_service import KpiSnapshotService
from analytics_platform.reports.report_generator import ReportGeneratorService
from analytics_platform.warehouse.ingestion_service import EventIngestionService
from analytics_platform.warehouse.metric_registry_service import MetricRegistryService

TENANT = "report-gen-tenant"


async def _seed_metric_and_kpi(repos, *, metric_key: str, kpi_name: str):
    """Takes a caller-supplied metric key and KPI name rather than a
    fixed one: `register_metric`/`register_kpi` are get-or-create with
    a commit-spanning lock (see their module docstrings), so exercising
    them through the rollback-isolated `repos` fixture durably commits
    everything written earlier in that same test -- a second test
    reusing the same metric key would see the first test's rollup
    history bleed into its own "since period_start" window."""
    registry = MetricRegistryService(repos)
    await registry.register_metric(TENANT, key=metric_key, name="Total Revenue", data_source="organizations", unit="currency_usd", aggregation_type="sum")
    ingestion = EventIngestionService(repos, registry=registry)
    end = datetime.now(timezone.utc)
    start = end - timedelta(hours=1)
    for v in (100.0, 200.0, 300.0):
        await ingestion.ingest_event(TENANT, metric_key=metric_key, data_source="organizations", value=v, occurred_at=start + timedelta(minutes=1))

    engine = AggregationEngine(repos)
    await engine.compute_rollup(
        TENANT, metric_key, domain="financial", period="daily", period_start=start, period_end=end, aggregation_type="sum",
    )

    kpi_service = KpiService(repos)
    kpi = await kpi_service.register_kpi(
        TENANT, name=kpi_name, scope="executive", metric_key=metric_key, target_value=1000.0,
        higher_is_better=True, threshold_warning=500.0, threshold_critical=200.0,
    )
    snapshot_service = KpiSnapshotService(repos, kpi_service=kpi_service)
    await snapshot_service.record_snapshot(TENANT, kpi.id, value=600.0)
    return kpi


@pytest.mark.asyncio
async def test_build_payload_executive_includes_metrics_and_kpis(repos):
    await _seed_metric_and_kpi(repos, metric_key="revenue.total.exec", kpi_name="Revenue Target Exec")
    generator = ReportGeneratorService(repos)
    payload = await generator.build_payload(TENANT, report_type="executive", config={"period": "daily"})

    assert payload["report_type"] == "executive"
    assert payload["tenant_id"] == TENANT
    assert any(m["metric_key"] == "revenue.total.exec" and m["domain"] == "financial" for m in payload["metrics"])
    assert any(k["name"] == "Revenue Target Exec" and k["current_value"] == 600.0 for k in payload["kpis"])
    assert "audit_summary" not in payload


@pytest.mark.asyncio
async def test_build_payload_security_includes_audit_summary(repos):
    generator = ReportGeneratorService(repos)
    payload = await generator.build_payload(TENANT, report_type="security", config={})
    assert payload["metrics"] == []
    assert payload["kpis"] == []
    assert "audit_summary" in payload
    assert payload["audit_summary"]["total_events"] == 0


@pytest.mark.asyncio
async def test_build_payload_config_overrides_defaults(repos):
    await _seed_metric_and_kpi(repos, metric_key="revenue.total.custom", kpi_name="Revenue Target Custom")
    generator = ReportGeneratorService(repos)
    # "custom" defaults to no domains/scopes; override to pull the financial domain explicitly.
    payload = await generator.build_payload(
        TENANT, report_type="custom", config={"domains": ["financial"], "metric_keys": ["revenue.total.custom"], "period": "daily"},
    )
    assert len(payload["metrics"]) == 1
    assert payload["metrics"][0]["value"] == 600.0


@pytest.mark.asyncio
async def test_build_payload_unknown_report_type_falls_back_to_custom_defaults(repos):
    generator = ReportGeneratorService(repos)
    payload = await generator.build_payload(TENANT, report_type="not_a_real_type", config={})
    assert payload["metrics"] == []
    assert payload["kpis"] == []
