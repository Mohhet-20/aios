"""Rule-based recommendation generation -- pure functions with no DB
access, mirroring the KPI Engine's `evaluate_health()` and the
Aggregation Engine's `_aggregate()` as another "real, non-stubbed
logic" module. Two signal sources feed the rule set: KPI health (from
Task #265's `KpiService.evaluate_health()`) and forecast results (from
Task #267's `ForecastJobService.run()`), which is why both take
already-computed dicts rather than re-deriving anything from raw
rollups themselves -- that keeps this module trivially testable and
free of any DB dependency."""
from __future__ import annotations

# Each KPI scope's default recommendation category when that KPI is
# unhealthy -- a KPI in "engineering" scope failing its threshold
# points at an infrastructure fix, one in "ai" scope points at prompt
# tuning, and so on. Falls back to "resource_allocation" for scopes
# without an obvious specific category (custom, organization).
CATEGORY_BY_KPI_SCOPE: dict[str, str] = {
    "engineering": "infrastructure_optimization",
    "ai": "prompt_optimization",
    "business": "cost_optimization",
    "executive": "resource_allocation",
    "workspace": "workflow_optimization",
    "organization": "capacity_planning",
    "custom": "resource_allocation",
}

# A forecast growing past this multiple of its own starting prediction
# over the horizon is considered a "steep" trend worth flagging --
# deliberately simple and disclosed, not a statistical significance test.
GROWTH_TREND_MULTIPLIER = 1.5


def recommendation_from_kpi_health(kpi: dict) -> dict | None:
    """`kpi` is the dict shape `KpiService`/`ReportGeneratorService`
    already produce: {kpi_id, name, scope, target_value, current_value,
    health}. Returns a recommendation candidate dict, or None if the
    KPI's health doesn't warrant one."""
    health = kpi.get("health")
    if health not in ("at_risk", "breached"):
        return None
    scope = kpi.get("scope", "custom")
    category = CATEGORY_BY_KPI_SCOPE.get(scope, "resource_allocation")
    impact = "critical" if health == "breached" else "medium"
    name = kpi.get("name", kpi.get("kpi_id", "unknown"))
    return {
        "category": category,
        "title": f"Address {health.replace('_', ' ')} KPI: {name}",
        "description": (
            f"KPI '{name}' (scope={scope}) is {health}: "
            f"current={kpi.get('current_value')}, target={kpi.get('target_value')}."
        ),
        "impact": impact,
        "evidence": {
            "kpi_id": kpi.get("kpi_id"),
            "health": health,
            "current_value": kpi.get("current_value"),
            "target_value": kpi.get("target_value"),
        },
    }


def recommendations_from_forecast(forecast: dict) -> list[dict]:
    """`forecast` is the `result` dict `ForecastJobService.run()`
    produces: {forecast_type, metric_key, predictions, anomalies_in_history, ...}.
    Returns zero or more recommendation candidate dicts."""
    recommendations: list[dict] = []
    metric_key = forecast.get("metric_key", "unknown")
    forecast_type = forecast.get("forecast_type", "usage")
    anomalies = forecast.get("anomalies_in_history") or []

    if anomalies:
        category = "security_improvement" if forecast_type == "risk" else "capacity_planning"
        recommendations.append({
            "category": category,
            "title": f"Investigate {len(anomalies)} anomal{'y' if len(anomalies) == 1 else 'ies'} in {metric_key}",
            "description": f"{len(anomalies)} historical data point(s) for '{metric_key}' deviated sharply from the series mean.",
            "impact": "high",
            "evidence": {"anomalies": anomalies, "metric_key": metric_key},
        })

    predictions = forecast.get("predictions") or []
    if len(predictions) >= 2:
        first_value = predictions[0].get("value", 0.0)
        last_value = predictions[-1].get("value", 0.0)
        if first_value > 0 and last_value >= first_value * GROWTH_TREND_MULTIPLIER:
            category = "capacity_planning" if forecast_type in ("capacity", "resource", "usage") else "cost_optimization"
            recommendations.append({
                "category": category,
                "title": f"Plan for projected growth in {metric_key}",
                "description": f"Forecast projects '{metric_key}' rising from {first_value} to {last_value} over the horizon.",
                "impact": "medium",
                "evidence": {"predictions": predictions, "metric_key": metric_key},
            })

    return recommendations
