"""Recommendation Engine service: create recommendations (directly, or
derived from KPI health / forecast results via `recommendation_rules.py`),
and drive the guarded open -> accepted/dismissed -> implemented
lifecycle on the domain-level `Recommendation` entity. Every accept/
dismiss/implement transition also writes a `RecommendationOutcomeModel`
row -- that outcome history is what lets the platform measure whether
its own suggestions are actually useful (acceptance-rate reporting)."""
from __future__ import annotations

from analytics_platform.core.exceptions import (
    RecommendationNotFoundError,
    UnsupportedRecommendationCategoryError,
    ValidationError,
)
from analytics_platform.database.base import utcnow
from analytics_platform.domain.entities import Recommendation
from analytics_platform.domain.enums import RecommendationCategory, RecommendationImpact, RecommendationStatus
from analytics_platform.models.observability import RecommendationOutcomeModel
from analytics_platform.models.recommendations import RecommendationModel
from analytics_platform.recommendations.recommendation_rules import recommendation_from_kpi_health, recommendations_from_forecast
from analytics_platform.repositories.registry import RepositoryRegistry


class RecommendationService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    def _assert_valid(self, *, category: str, impact: str) -> None:
        if category not in {c.value for c in RecommendationCategory}:
            raise UnsupportedRecommendationCategoryError(f"'{category}' is not a recognized recommendation category")
        if impact not in {i.value for i in RecommendationImpact}:
            raise ValidationError(f"'{impact}' is not a recognized recommendation impact")

    async def create_recommendation(
        self, tenant_id: str, *, category: str, title: str, description: str = "", impact: str = "medium", evidence: dict | None = None,
    ) -> RecommendationModel:
        self._assert_valid(category=category, impact=impact)
        recommendation = RecommendationModel(
            tenant_id=tenant_id, category=category, title=title, description=description,
            impact=impact, evidence=evidence or {}, status=RecommendationStatus.OPEN.value,
        )
        return await self.repos.recommendations.add(recommendation)

    async def generate_from_kpi(self, tenant_id: str, kpi: dict) -> RecommendationModel | None:
        candidate = recommendation_from_kpi_health(kpi)
        if candidate is None:
            return None
        return await self.create_recommendation(tenant_id, **candidate)

    async def generate_from_forecast(self, tenant_id: str, forecast: dict) -> list[RecommendationModel]:
        candidates = recommendations_from_forecast(forecast)
        return [await self.create_recommendation(tenant_id, **candidate) for candidate in candidates]

    async def get_or_404(self, tenant_id: str, recommendation_id: str) -> RecommendationModel:
        recommendation = await self.repos.recommendations.get_or_404(recommendation_id)
        if recommendation.tenant_id != tenant_id:
            raise RecommendationNotFoundError(f"Recommendation '{recommendation_id}' not found for tenant '{tenant_id}'")
        return recommendation

    async def list_for_tenant(self, tenant_id: str, *, category: str | None = None, status: str | None = None) -> list[RecommendationModel]:
        return await self.repos.recommendations.list_for_tenant(tenant_id, category=category, status=status)

    async def _apply_transition(
        self, tenant_id: str, recommendation_id: str, transition_name: str, outcome: str, *, terminal: bool,
    ) -> RecommendationModel:
        recommendation = await self.get_or_404(tenant_id, recommendation_id)
        entity = Recommendation(id=recommendation.id, status=RecommendationStatus(recommendation.status))
        getattr(entity, transition_name)()  # raises InvalidTransitionError on an illegal transition
        recommendation.status = entity.status.value
        if terminal:
            recommendation.resolved_at = utcnow()
        recommendation = await self.repos.recommendations.update(recommendation)
        await self.repos.recommendation_outcomes.add(
            RecommendationOutcomeModel(tenant_id=tenant_id, recommendation_id=recommendation.id, outcome=outcome)
        )
        return recommendation

    async def accept(self, tenant_id: str, recommendation_id: str) -> RecommendationModel:
        """Accepted is not a terminal state -- an accepted recommendation
        can still move on to implemented or dismissed later, so this
        does not set `resolved_at`, unlike dismiss()/implement()."""
        return await self._apply_transition(tenant_id, recommendation_id, "accept", "accepted", terminal=False)

    async def dismiss(self, tenant_id: str, recommendation_id: str) -> RecommendationModel:
        return await self._apply_transition(tenant_id, recommendation_id, "dismiss", "dismissed", terminal=True)

    async def implement(self, tenant_id: str, recommendation_id: str) -> RecommendationModel:
        return await self._apply_transition(tenant_id, recommendation_id, "implement", "implemented", terminal=True)
