from __future__ import annotations

from datetime import timedelta

import pytest

from observability_platform.core.exceptions import ComponentNotRegisteredError, ValidationError
from observability_platform.database.base import utcnow
from observability_platform.domain.enums import HealthStatus
from observability_platform.health.aggregation_service import HealthAggregationService
from observability_platform.health.healthcheck_service import HealthCheckService
from observability_platform.models.components import ComponentModel
from observability_platform.models.health import HealthCheckResultModel


@pytest.mark.asyncio
async def test_record_result_requires_registered_component(repos):
    svc = HealthCheckService(repos)
    with pytest.raises(ComponentNotRegisteredError):
        await svc.record_result("t1", "does-not-exist", status="healthy")


@pytest.mark.asyncio
async def test_record_result_rejects_unknown_status(repos):
    component = await repos.components.add(ComponentModel(tenant_id="t1", name="db", component_type="database"))
    svc = HealthCheckService(repos)
    with pytest.raises(ValidationError):
        await svc.record_result("t1", component.id, status="not-a-status")


@pytest.mark.asyncio
async def test_current_status_derives_from_latest_result(repos):
    component = await repos.components.add(ComponentModel(tenant_id="t1", name="db", component_type="database"))
    svc = HealthCheckService(repos)
    await svc.record_result("t1", component.id, status="degraded")
    await svc.record_result("t1", component.id, status="healthy")

    status = await svc.current_status("t1", component.id)
    assert status == HealthStatus.HEALTHY


@pytest.mark.asyncio
async def test_current_status_unknown_when_no_results(repos):
    component = await repos.components.add(ComponentModel(tenant_id="t1", name="db", component_type="database"))
    svc = HealthCheckService(repos)
    status = await svc.current_status("t1", component.id)
    assert status == HealthStatus.UNKNOWN


@pytest.mark.asyncio
async def test_current_status_unknown_when_stale(repos):
    component = await repos.components.add(ComponentModel(tenant_id="t1", name="db", component_type="database"))
    stale_result = HealthCheckResultModel(
        tenant_id="t1", component_id=component.id, status="healthy",
        checked_at=utcnow() - timedelta(seconds=99999),
    )
    await repos.health_check_results.add(stale_result)

    svc = HealthCheckService(repos)
    status = await svc.current_status("t1", component.id)
    assert status == HealthStatus.UNKNOWN


@pytest.mark.asyncio
async def test_overall_system_health_takes_worst_status(repos):
    healthy_comp = await repos.components.add(ComponentModel(tenant_id="t1", name="api", component_type="api_gateway"))
    unhealthy_comp = await repos.components.add(ComponentModel(tenant_id="t1", name="db", component_type="database"))
    svc = HealthCheckService(repos)
    await svc.record_result("t1", healthy_comp.id, status="healthy")
    await svc.record_result("t1", unhealthy_comp.id, status="unhealthy")

    agg = HealthAggregationService(repos)
    result = await agg.overall_system_health("t1")
    assert result["overall_status"] == "unhealthy"
    assert result["component_count"] == 2


@pytest.mark.asyncio
async def test_health_by_component_type_groups_correctly(repos):
    db1 = await repos.components.add(ComponentModel(tenant_id="t1", name="db1", component_type="database"))
    db2 = await repos.components.add(ComponentModel(tenant_id="t1", name="db2", component_type="database"))
    svc = HealthCheckService(repos)
    await svc.record_result("t1", db1.id, status="healthy")
    await svc.record_result("t1", db2.id, status="degraded")

    agg = HealthAggregationService(repos)
    by_type = await agg.health_by_component_type("t1")
    assert by_type["database"]["overall_status"] == "degraded"
    assert by_type["database"]["component_count"] == 2
