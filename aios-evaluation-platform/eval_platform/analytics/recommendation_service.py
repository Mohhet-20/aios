"""RecommendationService: CRUD + a simple OPEN -> ACCEPTED/DISMISSED
lifecycle for the AI Improvement Loop's output. Unlike `Alert`,
recommendations don't reopen or re-trigger — a dismissed or accepted
recommendation is a closed decision; a fresh analysis run creates a new
row rather than resurrecting an old one, so history stays intact."""
from __future__ import annotations

from eval_platform.core.exceptions import RecommendationError
from eval_platform.domain.enums import RecommendationCategory, RecommendationStatus
from eval_platform.models.analytics import RecommendationModel
from eval_platform.repositories.registry import RepositoryRegistry

_VALID_CATEGORIES = {c.value for c in RecommendationCategory}


class RecommendationService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_recommendation(
        self, workspace_id: str, *, category: str, target_type: str, title: str, description: str,
        target_id: str | None = None, evidence: dict | None = None,
    ) -> RecommendationModel:
        if category not in _VALID_CATEGORIES:
            raise RecommendationError(f"unknown category '{category}' (must be one of {sorted(_VALID_CATEGORIES)})")
        if not evidence:
            raise RecommendationError("a recommendation must be backed by non-empty 'evidence'")
        return await self.repos.recommendations.add(RecommendationModel(
            workspace_id=workspace_id, category=category, target_type=target_type, target_id=target_id,
            title=title, description=description, evidence=evidence,
        ))

    async def get_recommendation(self, recommendation_id: str) -> RecommendationModel:
        return await self.repos.recommendations.get_or_404(recommendation_id)

    async def list_recommendations(self, workspace_id: str, *, status: str | None = None, category: str | None = None) -> list[RecommendationModel]:
        return await self.repos.recommendations.list_for_workspace(workspace_id, status=status, category=category)

    async def accept(self, recommendation_id: str) -> RecommendationModel:
        return await self._resolve(recommendation_id, RecommendationStatus.ACCEPTED.value)

    async def dismiss(self, recommendation_id: str) -> RecommendationModel:
        return await self._resolve(recommendation_id, RecommendationStatus.DISMISSED.value)

    async def _resolve(self, recommendation_id: str, status: str) -> RecommendationModel:
        from eval_platform.database.base import utcnow

        recommendation = await self.repos.recommendations.get_or_404(recommendation_id)
        if recommendation.status != RecommendationStatus.OPEN.value:
            raise RecommendationError(f"recommendation '{recommendation_id}' is already {recommendation.status}, not open")
        recommendation.status = status
        recommendation.resolved_at = utcnow()
        return await self.repos.recommendations.update(recommendation)
