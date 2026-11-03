"""Forecast accuracy tracking: once a forecast's horizon has actually
passed, record what really happened next to what the Forecasting
Engine (Task #267) predicted, and compute the error. This is the
feedback loop that lets a team trust (or distrust) a given forecast
method for a given metric over time -- a forecast platform that never
checks its own predictions against reality is just a chart."""
from __future__ import annotations

from analytics_platform.core.exceptions import ValidationError
from analytics_platform.models.forecasts import ForecastJobModel
from analytics_platform.models.observability import ForecastAccuracyModel
from analytics_platform.repositories.registry import RepositoryRegistry


def compute_error_pct(*, predicted_value: float, actual_value: float) -> float:
    """Absolute percentage error. When the actual value is exactly
    zero the usual formula divides by zero -- disclosed convention
    here is 0% error if the prediction was also (near) zero, 100%
    error otherwise, rather than raising or returning infinity."""
    if actual_value == 0:
        return 0.0 if predicted_value == 0 else 100.0
    return abs(actual_value - predicted_value) / abs(actual_value) * 100.0


class ForecastAccuracyService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record_accuracy(
        self, tenant_id: str, *, forecast_job_id: str, predicted_value: float, actual_value: float,
    ) -> ForecastAccuracyModel:
        entry = ForecastAccuracyModel(
            tenant_id=tenant_id, forecast_job_id=forecast_job_id, predicted_value=predicted_value,
            actual_value=actual_value, error_pct=compute_error_pct(predicted_value=predicted_value, actual_value=actual_value),
        )
        return await self.repos.forecast_accuracy.add(entry)

    async def record_from_job(
        self, tenant_id: str, job: ForecastJobModel, *, step: int, actual_value: float,
    ) -> ForecastAccuracyModel:
        """Pulls the predicted value for `step` (1-indexed, matching the
        `step` field `ForecastJobService.run()` writes into `result["predictions"]`)
        straight off an already-completed job, so the caller doesn't have
        to re-derive it."""
        predictions = job.result.get("predictions", []) if job.result else []
        matches = [p for p in predictions if p.get("step") == step]
        if not matches:
            raise ValidationError(f"forecast job '{job.id}' has no prediction for step {step}")
        predicted_value = matches[0]["value"]
        return await self.record_accuracy(tenant_id, forecast_job_id=job.id, predicted_value=predicted_value, actual_value=actual_value)

    async def list_for_job(self, tenant_id: str, forecast_job_id: str) -> list[ForecastAccuracyModel]:
        return await self.repos.forecast_accuracy.list_for_job(tenant_id, forecast_job_id)

    async def average_error(self, tenant_id: str, forecast_job_id: str) -> float:
        entries = await self.list_for_job(tenant_id, forecast_job_id)
        if not entries:
            return 0.0
        return sum(entry.error_pct for entry in entries) / len(entries)
