from __future__ import annotations

import pytest

from analytics_platform.core.exceptions import (
    InvalidTransitionError,
    RecommendationNotFoundError,
    UnsupportedRecommendationCategoryError,
    ValidationError,
)
from analytics_platform.recommendations.recommendation_service import RecommendationService

TENANT = "rec-tenant"


@pytest.mark.asyncio
async def test_create_recommendation_rejects_bad_category(repos):
    service = RecommendationService(repos)
    with pytest.raises(UnsupportedRecommendationCategoryError):
        await service.create_recommendation(TENANT, category="not_a_category", title="Bad")


@pytest.mark.asyncio
async def test_create_recommendation_rejects_bad_impact(repos):
    service = RecommendationService(repos)
    with pytest.raises(ValidationError):
        await service.create_recommendation(TENANT, category="cost_optimization", title="Bad", impact="extreme")


@pytest.mark.asyncio
async def test_generate_from_kpi_returns_none_when_healthy(repos):
    service = RecommendationService(repos)
    kpi = {"kpi_id": "k1", "name": "Retention", "scope": "business", "health": "on_target"}
    assert await service.generate_from_kpi(TENANT, kpi) is None


@pytest.mark.asyncio
async def test_generate_from_kpi_creates_recommendation(repos):
    service = RecommendationService(repos)
    kpi = {"kpi_id": "k1", "name": "Error Rate", "scope": "engineering", "health": "breached", "current_value": 0.2, "target_value": 0.01}
    rec = await service.generate_from_kpi(TENANT, kpi)
    assert rec is not None
    assert rec.category == "infrastructure_optimization"
    assert rec.status == "open"


@pytest.mark.asyncio
async def test_generate_from_forecast_creates_multiple(repos):
    service = RecommendationService(repos)
    forecast = {
        "forecast_type": "cost", "metric_key": "spend.total",
        "predictions": [{"step": 1, "value": 100.0}, {"step": 2, "value": 300.0}],
        "anomalies_in_history": [{"index": 0, "value": 999.0, "z_score": 4.0}],
    }
    recs = await service.generate_from_forecast(TENANT, forecast)
    assert len(recs) == 2


@pytest.mark.asyncio
async def test_full_lifecycle_accept_then_implement_records_outcomes(repos):
    service = RecommendationService(repos)
    rec = await service.create_recommendation(TENANT, category="cost_optimization", title="Cut idle capacity")

    accepted = await service.accept(TENANT, rec.id)
    assert accepted.status == "accepted"
    assert accepted.resolved_at is None

    implemented = await service.implement(TENANT, rec.id)
    assert implemented.status == "implemented"
    assert implemented.resolved_at is not None

    outcomes = await repos.recommendation_outcomes.list(filters={"recommendation_id": rec.id})
    outcome_values = {o.outcome for o in outcomes}
    assert outcome_values == {"accepted", "implemented"}


@pytest.mark.asyncio
async def test_dismiss_from_open_records_outcome(repos):
    service = RecommendationService(repos)
    rec = await service.create_recommendation(TENANT, category="capacity_planning", title="Scale down")
    dismissed = await service.dismiss(TENANT, rec.id)
    assert dismissed.status == "dismissed"
    assert dismissed.resolved_at is not None


@pytest.mark.asyncio
async def test_implement_without_accept_raises(repos):
    service = RecommendationService(repos)
    rec = await service.create_recommendation(TENANT, category="workflow_optimization", title="Automate step")
    with pytest.raises(InvalidTransitionError):
        await service.implement(TENANT, rec.id)


@pytest.mark.asyncio
async def test_not_found_for_other_tenant(repos):
    service = RecommendationService(repos)
    rec = await service.create_recommendation(TENANT, category="security_improvement", title="Rotate keys")
    with pytest.raises(RecommendationNotFoundError):
        await service.accept("other-tenant", rec.id)


@pytest.mark.asyncio
async def test_list_for_tenant_filters_by_category_and_status(repos):
    service = RecommendationService(repos)
    a = await service.create_recommendation(TENANT, category="cost_optimization", title="A")
    await service.create_recommendation(TENANT, category="capacity_planning", title="B")
    await service.accept(TENANT, a.id)

    cost_only = await service.list_for_tenant(TENANT, category="cost_optimization")
    assert len(cost_only) == 1
    accepted_only = await service.list_for_tenant(TENANT, status="accepted")
    assert len(accepted_only) == 1
