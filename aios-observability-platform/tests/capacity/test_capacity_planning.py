from __future__ import annotations

from datetime import timedelta

import pytest

from observability_platform.capacity.forecast_service import CapacityForecastService
from observability_platform.core.exceptions import InsufficientHistoryError
from observability_platform.database.base import utcnow
from observability_platform.models.capacity import CapacitySnapshotModel


async def _seed_linear_growth(repos, tenant_id="t1", resource_type="storage", days=10, start=100.0, daily_growth=10.0):
    now = utcnow()
    for i in range(days):
        snapshot = CapacitySnapshotModel(
            tenant_id=tenant_id, resource_type=resource_type, value=start + i * daily_growth,
            captured_at=now - timedelta(days=days - i),
        )
        await repos.capacity_snapshots.add(snapshot)


@pytest.mark.asyncio
async def test_forecast_requires_minimum_history(repos):
    svc = CapacityForecastService(repos)
    await _seed_linear_growth(repos, days=2)
    with pytest.raises(InsufficientHistoryError):
        await svc.generate_forecast("t1", "storage")


@pytest.mark.asyncio
async def test_forecast_projects_upward_trend(repos):
    svc = CapacityForecastService(repos)
    await _seed_linear_growth(repos, days=10, start=100.0, daily_growth=10.0)

    forecast = await svc.generate_forecast("t1", "storage", horizon_days=30)
    assert forecast.method == "linear_trend"
    assert len(forecast.points) > 0
    # Values should be increasing since we seeded steady growth.
    values = [p["projected_value"] for p in forecast.points]
    assert values == sorted(values)
    assert values[-1] > values[0]


@pytest.mark.asyncio
async def test_forecast_computes_exhaustion_date_when_limit_given(repos):
    svc = CapacityForecastService(repos)
    await _seed_linear_growth(repos, days=10, start=100.0, daily_growth=10.0)

    forecast = await svc.generate_forecast("t1", "storage", horizon_days=90, capacity_limit=500.0)
    assert forecast.projected_exhaustion_at is not None
    assert forecast.projected_exhaustion_at > utcnow()


@pytest.mark.asyncio
async def test_scaling_recommendation_flags_scale_up_near_limit(repos):
    svc = CapacityForecastService(repos)
    await _seed_linear_growth(repos, days=10, start=100.0, daily_growth=10.0)

    svc.settings.capacity_growth_alert_threshold_pct = 50.0
    rec = await svc.scaling_recommendation("t1", "storage", capacity_limit=200.0)
    assert rec["recommendation"] == "scale_up"


@pytest.mark.asyncio
async def test_scaling_recommendation_no_action_when_far_from_limit(repos):
    svc = CapacityForecastService(repos)
    await _seed_linear_growth(repos, days=10, start=100.0, daily_growth=1.0)

    rec = await svc.scaling_recommendation("t1", "storage", capacity_limit=100000.0)
    assert rec["recommendation"] == "no_action"


@pytest.mark.asyncio
async def test_scaling_recommendation_without_limit_reports_trend(repos):
    svc = CapacityForecastService(repos)
    await _seed_linear_growth(repos, days=10)
    rec = await svc.scaling_recommendation("t1", "storage")
    assert rec["recommendation"] == "monitor"
    assert "trend" in rec
