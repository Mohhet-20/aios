"""Forecasting Engine: request -> queued, run() drives the guarded
queued -> running -> completed/failed lifecycle on the domain-level
`ForecastJob` entity while pulling real historical rollup data (Task
#264's Aggregation Engine output) and projecting it forward with one
of three real statistical methods (forecast_methods.py). Each forecast
type the prompt specifies (usage, cost, capacity, growth, resource,
performance_trend, anomaly, risk) has a default analytics domain +
rollup period it forecasts from -- the same "type has a sensible
default pull set" precedent the Report Engine established."""
from __future__ import annotations


from analytics_platform.config.settings import Settings, get_settings
from analytics_platform.core.exceptions import (
    ForecastGenerationFailedError,
    ForecastNotFoundError,
    InsufficientHistoryError,
    InvalidTransitionError,
    UnsupportedForecastTypeError,
    ValidationError,
)
from analytics_platform.domain.entities import ForecastJob
from analytics_platform.domain.enums import ForecastJobStatus, ForecastMethod, ForecastType
from analytics_platform.forecasting.forecast_methods import FORECAST_METHODS, detect_anomalies
from analytics_platform.models.forecasts import ForecastJobModel
from analytics_platform.repositories.registry import RepositoryRegistry
from analytics_platform.clock import utc_now

# (analytics domain, rollup period) each forecast type pulls history from by
# default -- overridable per-call since a definition-level override isn't
# available on this model (ForecastJobModel has no domain/period column).
FORECAST_TYPE_DEFAULTS: dict[str, tuple[str, str]] = {
    "usage": ("business", "daily"),
    "cost": ("financial", "daily"),
    "capacity": ("performance", "daily"),
    "growth": ("business", "monthly"),
    "resource": ("performance", "daily"),
    "performance_trend": ("performance", "daily"),
    "anomaly": ("performance", "hourly"),
    "risk": ("business", "weekly"),
}


class ForecastJobService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    def _assert_valid(self, *, forecast_type: str, method: str) -> None:
        if forecast_type not in {t.value for t in ForecastType}:
            raise UnsupportedForecastTypeError(f"'{forecast_type}' is not a recognized forecast type")
        if method not in {m.value for m in ForecastMethod}:
            raise ValidationError(f"'{method}' is not a recognized forecast method")

    async def request_job(
        self, tenant_id: str, *, forecast_type: str, metric_key: str, method: str = "linear_regression", horizon_days: int = 30,
    ) -> ForecastJobModel:
        self._assert_valid(forecast_type=forecast_type, method=method)
        if horizon_days <= 0:
            raise ValidationError("horizon_days must be positive")
        job = ForecastJobModel(
            tenant_id=tenant_id, forecast_type=forecast_type, method=method, metric_key=metric_key,
            horizon_days=horizon_days, status=ForecastJobStatus.QUEUED.value,
        )
        return await self.repos.forecast_jobs.add(job)

    async def get_or_404(self, tenant_id: str, job_id: str) -> ForecastJobModel:
        job = await self.repos.forecast_jobs.get_or_404(job_id)
        if job.tenant_id != tenant_id:
            raise ForecastNotFoundError(f"Forecast job '{job_id}' not found for tenant '{tenant_id}'")
        return job

    async def _apply_transition(self, tenant_id: str, job_id: str, transition_name: str) -> ForecastJobModel:
        job = await self.get_or_404(tenant_id, job_id)
        entity = ForecastJob(id=job.id, status=ForecastJobStatus(job.status))
        try:
            getattr(entity, transition_name)()
        except InvalidTransitionError as exc:
            raise ForecastGenerationFailedError(str(exc)) from exc
        job.status = entity.status.value
        return job

    async def start(self, tenant_id: str, job_id: str) -> ForecastJobModel:
        job = await self._apply_transition(tenant_id, job_id, "start")
        return await self.repos.forecast_jobs.update(job)

    async def complete(self, tenant_id: str, job_id: str, *, result: dict) -> ForecastJobModel:
        job = await self._apply_transition(tenant_id, job_id, "complete")
        job.result = result
        job.completed_at = utc_now()
        return await self.repos.forecast_jobs.update(job)

    async def fail(self, tenant_id: str, job_id: str, *, error: str) -> ForecastJobModel:
        job = await self._apply_transition(tenant_id, job_id, "fail")
        job.error = error
        job.completed_at = utc_now()
        return await self.repos.forecast_jobs.update(job)

    async def run(self, tenant_id: str, job_id: str) -> ForecastJobModel:
        await self.start(tenant_id, job_id)
        job = await self.get_or_404(tenant_id, job_id)
        domain, period = FORECAST_TYPE_DEFAULTS.get(job.forecast_type, ("business", "daily"))

        try:
            rollups = await self.repos.metric_rollups.list_for_metric(tenant_id, job.metric_key, domain=domain, period=period, limit=500)
            values = [r.value for r in rollups]
            if len(values) < self.settings.forecast_min_history_points:
                raise InsufficientHistoryError(
                    f"forecast for '{job.metric_key}' needs at least {self.settings.forecast_min_history_points} rollup points, found {len(values)}"
                )
            forecast_fn = FORECAST_METHODS[job.method]
            predictions = forecast_fn(values, job.horizon_days)
        except Exception as exc:  # noqa: BLE001 - any assembly failure should fail the job, not crash the caller
            return await self.fail(tenant_id, job_id, error=str(exc))

        result = {
            "forecast_type": job.forecast_type,
            "method": job.method,
            "metric_key": job.metric_key,
            "domain": domain,
            "period": period,
            "history_points": len(values),
            "horizon": job.horizon_days,
            "predictions": [{"step": step + 1, "value": value} for step, value in enumerate(predictions)],
            "anomalies_in_history": detect_anomalies(values),
            "generated_at": utc_now().isoformat(),
        }
        return await self.complete(tenant_id, job_id, result=result)

    async def list_for_tenant(self, tenant_id: str, *, forecast_type: str | None = None) -> list[ForecastJobModel]:
        return await self.repos.forecast_jobs.list_for_tenant(tenant_id, forecast_type=forecast_type)
