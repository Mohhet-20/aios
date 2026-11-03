from __future__ import annotations

import pytest

from analytics_platform.observability.recommendation_analytics_service import RecommendationAnalyticsService
from analytics_platform.recommendations.recommendation_service import RecommendationService

TENANT = "rec-analytics-tenant"


@pytest.mark.asyncio
async def test_acceptance_rate_no_outcomes_is_zero(repos):
    service = RecommendationAnalyticsService(repos)
    assert await service.acceptance_rate(TENANT) == 0.0


@pytest.mark.asyncio
async def test_acceptance_rate_and_breakdown(repos):
    recs = RecommendationService(repos)
    a = await recs.create_recommendation(TENANT, category="cost_optimization", title="A")
    b = await recs.create_recommendation(TENANT, category="capacity_planning", title="B")
    c = await recs.create_recommendation(TENANT, category="workflow_optimization", title="C")

    await recs.accept(TENANT, a.id)
    await recs.implement(TENANT, a.id)
    await recs.dismiss(TENANT, b.id)
    await recs.accept(TENANT, c.id)

    analytics = RecommendationAnalyticsService(repos)
    breakdown = await analytics.outcome_breakdown(TENANT)
    assert breakdown == {"accepted": 2, "implemented": 1, "dismissed": 1}

    rate = await analytics.acceptance_rate(TENANT)
    assert rate == pytest.approx(3 / 4)
