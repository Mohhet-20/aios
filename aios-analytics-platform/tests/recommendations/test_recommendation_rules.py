from __future__ import annotations

from analytics_platform.recommendations.recommendation_rules import (
    recommendation_from_kpi_health,
    recommendations_from_forecast,
)


def test_recommendation_from_kpi_health_none_when_on_target():
    kpi = {"kpi_id": "k1", "name": "Retention", "scope": "business", "health": "on_target", "current_value": 0.9, "target_value": 0.9}
    assert recommendation_from_kpi_health(kpi) is None


def test_recommendation_from_kpi_health_breached_is_critical():
    kpi = {"kpi_id": "k1", "name": "Error Rate", "scope": "engineering", "health": "breached", "current_value": 0.2, "target_value": 0.01}
    rec = recommendation_from_kpi_health(kpi)
    assert rec["category"] == "infrastructure_optimization"
    assert rec["impact"] == "critical"
    assert rec["evidence"]["kpi_id"] == "k1"


def test_recommendation_from_kpi_health_at_risk_is_medium():
    kpi = {"kpi_id": "k2", "name": "Token Cost", "scope": "ai", "health": "at_risk", "current_value": 500, "target_value": 300}
    rec = recommendation_from_kpi_health(kpi)
    assert rec["category"] == "prompt_optimization"
    assert rec["impact"] == "medium"


def test_recommendation_from_kpi_health_unknown_scope_falls_back():
    kpi = {"kpi_id": "k3", "name": "Custom Thing", "scope": "custom", "health": "breached"}
    rec = recommendation_from_kpi_health(kpi)
    assert rec["category"] == "resource_allocation"


def test_recommendations_from_forecast_no_signal_is_empty():
    forecast = {"forecast_type": "usage", "metric_key": "x", "predictions": [], "anomalies_in_history": []}
    assert recommendations_from_forecast(forecast) == []


def test_recommendations_from_forecast_anomalies_flagged():
    forecast = {
        "forecast_type": "risk", "metric_key": "login.failures",
        "predictions": [{"step": 1, "value": 10.0}],
        "anomalies_in_history": [{"index": 5, "value": 500.0, "z_score": 3.1}],
    }
    recs = recommendations_from_forecast(forecast)
    assert len(recs) == 1
    assert recs[0]["category"] == "security_improvement"


def test_recommendations_from_forecast_growth_trend_flagged():
    forecast = {
        "forecast_type": "capacity", "metric_key": "storage.gb",
        "predictions": [{"step": 1, "value": 100.0}, {"step": 2, "value": 200.0}],
        "anomalies_in_history": [],
    }
    recs = recommendations_from_forecast(forecast)
    assert len(recs) == 1
    assert recs[0]["category"] == "capacity_planning"


def test_recommendations_from_forecast_both_signals_produce_two():
    forecast = {
        "forecast_type": "cost", "metric_key": "spend.total",
        "predictions": [{"step": 1, "value": 100.0}, {"step": 2, "value": 300.0}],
        "anomalies_in_history": [{"index": 0, "value": 999.0, "z_score": 4.0}],
    }
    recs = recommendations_from_forecast(forecast)
    assert len(recs) == 2
    categories = {r["category"] for r in recs}
    assert "capacity_planning" in categories
    assert "cost_optimization" in categories
