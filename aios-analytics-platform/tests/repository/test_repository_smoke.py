from __future__ import annotations

import pytest

from analytics_platform.models.dashboards import DashboardModel
from analytics_platform.models.forecasts import ForecastJobModel
from analytics_platform.models.kpis import KpiDefinitionModel
from analytics_platform.models.recommendations import RecommendationModel
from analytics_platform.models.reports import ReportDefinitionModel
from analytics_platform.models.warehouse import MetricDefinitionModel

TENANT = "smoke-tenant"


@pytest.mark.asyncio
async def test_metric_definition_crud(repos):
    metric = MetricDefinitionModel(tenant_id=TENANT, key="api.latency", name="API Latency", data_source="api_gateway")
    metric = await repos.metric_definitions.add(metric)
    fetched = await repos.metric_definitions.get(metric.id)
    assert fetched is not None
    assert fetched.key == "api.latency"

    by_key = await repos.metric_definitions.get_by_key(TENANT, "api.latency")
    assert by_key is not None and by_key.id == metric.id


@pytest.mark.asyncio
async def test_kpi_definition_crud(repos):
    kpi = KpiDefinitionModel(tenant_id=TENANT, name="Active Users", scope="business", metric_key="users.active", target_value=1000)
    kpi = await repos.kpi_definitions.add(kpi)
    found = await repos.kpi_definitions.list_for_tenant(TENANT, scope="business")
    assert any(k.id == kpi.id for k in found)


@pytest.mark.asyncio
async def test_report_definition_crud(repos):
    report = ReportDefinitionModel(tenant_id=TENANT, name="Weekly Exec Report", report_type="executive")
    report = await repos.report_definitions.add(report)
    found = await repos.report_definitions.list_for_tenant(TENANT, report_type="executive")
    assert any(r.id == report.id for r in found)


@pytest.mark.asyncio
async def test_forecast_job_crud(repos):
    job = ForecastJobModel(tenant_id=TENANT, forecast_type="cost", metric_key="infra.cost")
    job = await repos.forecast_jobs.add(job)
    found = await repos.forecast_jobs.list_for_tenant(TENANT, forecast_type="cost")
    assert any(j.id == job.id for j in found)


@pytest.mark.asyncio
async def test_recommendation_crud(repos):
    rec = RecommendationModel(tenant_id=TENANT, category="cost_optimization", title="Right-size instances")
    rec = await repos.recommendations.add(rec)
    found = await repos.recommendations.list_for_tenant(TENANT, category="cost_optimization")
    assert any(r.id == rec.id for r in found)


@pytest.mark.asyncio
async def test_dashboard_crud(repos):
    dash = DashboardModel(tenant_id=TENANT, name="Executive Overview")
    dash = await repos.dashboards.add(dash)
    found = await repos.dashboards.list_for_tenant(TENANT)
    assert any(d.id == dash.id for d in found)
