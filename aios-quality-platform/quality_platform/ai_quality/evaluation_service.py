"""Raw evaluation score recording — the time series a regression scan
reads its "current score" from."""
from __future__ import annotations

from quality_platform.config.settings import get_settings
from quality_platform.core.exceptions import UnsupportedAiQualityDimensionError
from quality_platform.models.ai_quality import AiQualityEvaluationModel
from quality_platform.repositories.registry import RepositoryRegistry


class EvaluationService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    def _validate_dimension(self, dimension: str) -> None:
        if dimension not in self.settings.ai_quality_dimensions:
            raise UnsupportedAiQualityDimensionError(f"Unsupported AI quality dimension '{dimension}'")

    async def record_evaluation(
        self, tenant_id: str, dimension: str, subject_ref: str, *, score: float
    ) -> AiQualityEvaluationModel:
        self._validate_dimension(dimension)
        evaluation = AiQualityEvaluationModel(tenant_id=tenant_id, dimension=dimension, subject_ref=subject_ref, score=score)
        return await self.repos.ai_quality_evaluations.add(evaluation)

    async def list_for_subject(
        self, tenant_id: str, dimension: str, subject_ref: str, *, limit: int = 200
    ) -> list[AiQualityEvaluationModel]:
        return await self.repos.ai_quality_evaluations.list_for_subject(tenant_id, dimension, subject_ref, limit=limit)

    async def latest_score(self, tenant_id: str, dimension: str, subject_ref: str) -> float | None:
        recent = await self.list_for_subject(tenant_id, dimension, subject_ref, limit=1)
        return recent[0].score if recent else None
