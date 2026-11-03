from __future__ import annotations

import pytest

from analytics_platform.core.exceptions import KpiNotFoundError, ValidationError
from analytics_platform.domain.enums import KpiHealth
from analytics_platform.kpis.kpi_service import KpiService

TENANT = "kpi-tenant"


@pytest.mark.asyncio
async def test_register_kpi_idempotent_by_name(repos):
    service = KpiService(repos)
    a = await service.register_kpi(TENANT, name="Active Users", scope="business", metric_key="users.active", target_value=1000)
    b = await service.register_kpi(TENANT, name="Active Users", scope="business", metric_key="users.active", target_value=2000)
    assert a.id == b.id


@pytest.mark.asyncio
async def test_register_kpi_rejects_bad_scope(repos):
    service = KpiService(repos)
    with pytest.raises(ValidationError):
        await service.register_kpi(TENANT, name="Bad", scope="not_a_scope", metric_key="x", target_value=1)


@pytest.mark.asyncio
async def test_archive_and_reactivate(repos):
    service = KpiService(repos)
    kpi = await service.register_kpi(TENANT, name="Automation Rate", scope="engineering", metric_key="automation.rate", target_value=0.8)
    archived = await service.archive_kpi(TENANT, kpi.id)
    assert archived.status == "archived"
    reactivated = await service.reactivate_kpi(TENANT, kpi.id)
    assert reactivated.status == "active"


@pytest.mark.asyncio
async def test_not_found_for_other_tenant(repos):
    service = KpiService(repos)
    kpi = await service.register_kpi(TENANT, name="Cost Per User", scope="executive", metric_key="cost.per_user", target_value=5.0)
    with pytest.raises(KpiNotFoundError):
        await service.archive_kpi("other-tenant", kpi.id)


@pytest.mark.asyncio
async def test_evaluate_health_higher_is_better(repos):
    service = KpiService(repos)
    kpi = await service.register_kpi(
        TENANT, name="Retention", scope="business", metric_key="users.retention", target_value=0.9,
        higher_is_better=True, threshold_warning=0.7, threshold_critical=0.5,
    )
    assert service.evaluate_health(kpi, 0.95) == KpiHealth.ON_TARGET.value
    assert service.evaluate_health(kpi, 0.6) == KpiHealth.AT_RISK.value
    assert service.evaluate_health(kpi, 0.3) == KpiHealth.BREACHED.value


@pytest.mark.asyncio
async def test_evaluate_health_lower_is_better(repos):
    service = KpiService(repos)
    kpi = await service.register_kpi(
        TENANT, name="Error Rate", scope="engineering", metric_key="api.error_rate", target_value=0.01,
        higher_is_better=False, threshold_warning=0.05, threshold_critical=0.10,
    )
    assert service.evaluate_health(kpi, 0.01) == KpiHealth.ON_TARGET.value
    assert service.evaluate_health(kpi, 0.07) == KpiHealth.AT_RISK.value
    assert service.evaluate_health(kpi, 0.20) == KpiHealth.BREACHED.value


@pytest.mark.asyncio
async def test_evaluate_health_no_thresholds_is_always_on_target(repos):
    service = KpiService(repos)
    kpi = await service.register_kpi(TENANT, name="No Thresholds", scope="custom", metric_key="x.y", target_value=1.0)
    assert service.evaluate_health(kpi, 999.0) == KpiHealth.ON_TARGET.value
