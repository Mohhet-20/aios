"""Capacity planning: records periodic resource-usage snapshots and
projects future usage from them.

`method="linear_trend"` is the honest, disclosed scope of the
forecasting here: ordinary least-squares linear regression over the
historical snapshots, projected forward. This is a real, working
forecast — reasonable for roughly-linear growth (steady traffic ramp,
steady storage accumulation) — but it is NOT a seasonal or ML-based
forecasting model, and callers with genuinely cyclical or bursty
resource usage should not expect it to capture that shape. A real
forecasting engine (e.g. Prophet-style seasonal decomposition) is a
natural drop-in replacement behind `_fit_linear_trend` without
touching any caller, the same "disclosed gap with a clear extension
point" posture as every other approximation in this platform."""
from __future__ import annotations

from datetime import datetime, timedelta

from observability_platform.config.settings import Settings, get_settings
from observability_platform.core.exceptions import InsufficientHistoryError
from observability_platform.database.base import utcnow
from observability_platform.models.capacity import CapacityForecastModel, CapacitySnapshotModel
from observability_platform.repositories.registry import RepositoryRegistry


def _fit_linear_trend(points: list[tuple[datetime, float]]) -> tuple[float, float]:
    """Returns (slope_per_day, intercept) for y = slope*x + intercept,
    where x is days elapsed since the first point."""
    t0 = points[0][0]
    xs = [(t - t0).total_seconds() / 86400 for t, _ in points]
    ys = [v for _, v in points]
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    slope = numerator / denominator if denominator else 0.0
    intercept = mean_y - slope * mean_x
    return slope, intercept


class CapacityForecastService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def record_snapshot(
        self, tenant_id: str, resource_type: str, value: float, *, unit: str | None = None, component_id: str | None = None
    ) -> CapacitySnapshotModel:
        snapshot = CapacitySnapshotModel(tenant_id=tenant_id, resource_type=resource_type, value=value, unit=unit, component_id=component_id)
        return await self.repos.capacity_snapshots.add(snapshot)

    async def history(
        self, tenant_id: str, resource_type: str, *, component_id: str | None = None, since: datetime | None = None
    ) -> list[CapacitySnapshotModel]:
        return await self.repos.capacity_snapshots.history(tenant_id, resource_type, component_id=component_id, since=since)

    async def generate_forecast(
        self,
        tenant_id: str,
        resource_type: str,
        *,
        component_id: str | None = None,
        horizon_days: int | None = None,
        capacity_limit: float | None = None,
    ) -> CapacityForecastModel:
        horizon = horizon_days or self.settings.capacity_forecast_horizon_days
        snapshots = await self.history(tenant_id, resource_type, component_id=component_id)
        if len(snapshots) < self.settings.capacity_forecast_min_history_points:
            raise InsufficientHistoryError(
                f"Need at least {self.settings.capacity_forecast_min_history_points} historical snapshots to "
                f"forecast '{resource_type}', found {len(snapshots)}"
            )

        series = [(s.captured_at, s.value) for s in snapshots]
        slope, intercept = _fit_linear_trend(series)
        t0 = series[0][0]

        def project(days_from_t0: float) -> float:
            return slope * days_from_t0 + intercept

        last_offset = (series[-1][0] - t0).total_seconds() / 86400
        sample_count = min(horizon, 10) or 1
        step = horizon / sample_count
        points = []
        for i in range(1, sample_count + 1):
            offset = last_offset + i * step
            points.append({
                "days_from_now": round(i * step, 1),
                "projected_value": round(project(offset), 4),
            })

        projected_exhaustion_at = None
        if capacity_limit is not None and slope > 0:
            current_value = project(last_offset)
            if current_value < capacity_limit:
                days_to_exhaustion = (capacity_limit - intercept) / slope - last_offset
                if days_to_exhaustion > 0:
                    projected_exhaustion_at = utcnow() + timedelta(days=days_to_exhaustion)

        forecast = CapacityForecastModel(
            tenant_id=tenant_id, resource_type=resource_type, component_id=component_id,
            horizon_days=horizon, method="linear_trend", points=points,
            projected_exhaustion_at=projected_exhaustion_at,
        )
        return await self.repos.capacity_forecasts.add(forecast)

    async def scaling_recommendation(
        self,
        tenant_id: str,
        resource_type: str,
        *,
        component_id: str | None = None,
        capacity_limit: float | None = None,
    ) -> dict:
        """A plain-language recommendation derived from the forecast:
        flags for scaling once the projected end-of-horizon value
        crosses `capacity_growth_alert_threshold_pct` of the supplied
        capacity limit (if given), or simply reports the trend
        direction and magnitude when no limit is supplied."""
        forecast = await self.generate_forecast(
            tenant_id, resource_type, component_id=component_id, capacity_limit=capacity_limit
        )
        if not forecast.points:
            return {"recommendation": "insufficient_data"}

        end_of_horizon_value = forecast.points[-1]["projected_value"]
        if capacity_limit is not None:
            pct_of_limit = (end_of_horizon_value / capacity_limit * 100) if capacity_limit else 0.0
            if pct_of_limit >= self.settings.capacity_growth_alert_threshold_pct:
                return {
                    "recommendation": "scale_up",
                    "reason": f"Projected usage reaches {pct_of_limit:.1f}% of capacity within {forecast.horizon_days} days",
                    "projected_exhaustion_at": forecast.projected_exhaustion_at.isoformat() if forecast.projected_exhaustion_at else None,
                }
            return {"recommendation": "no_action", "reason": f"Projected usage stays at {pct_of_limit:.1f}% of capacity"}

        return {"recommendation": "monitor", "reason": "No capacity limit supplied — trend reported only", "trend": forecast.points}
