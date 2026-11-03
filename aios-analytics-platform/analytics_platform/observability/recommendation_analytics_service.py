"""Recommendation-outcome analytics: reads the `RecommendationOutcomeModel`
rows `RecommendationService` (Task #268) writes on every accept/dismiss/
implement, and turns them into an acceptance-rate summary. This is the
"whether its own suggestions are actually useful" measurement the
Recommendation Engine's own module docstring points to observability
for."""
from __future__ import annotations

from analytics_platform.repositories.registry import RepositoryRegistry


class RecommendationAnalyticsService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def outcome_breakdown(self, tenant_id: str, *, limit: int = 500) -> dict[str, int]:
        outcomes = await self.repos.recommendation_outcomes.list_recent(tenant_id, limit=limit)
        breakdown: dict[str, int] = {}
        for outcome in outcomes:
            breakdown[outcome.outcome] = breakdown.get(outcome.outcome, 0) + 1
        return breakdown

    async def acceptance_rate(self, tenant_id: str, *, limit: int = 500) -> float:
        """Fraction of recorded outcomes that were "accepted" or
        "implemented" rather than "dismissed". A recommendation that
        was accepted and later implemented produces two outcome rows
        (that's intentional -- it's a full history, not just a final
        state), so this counts outcome *events*, not distinct
        recommendations."""
        breakdown = await self.outcome_breakdown(tenant_id, limit=limit)
        total = sum(breakdown.values())
        if total == 0:
            return 0.0
        positive = breakdown.get("accepted", 0) + breakdown.get("implemented", 0)
        return positive / total
