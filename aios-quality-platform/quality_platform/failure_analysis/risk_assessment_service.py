"""Risk assessment scoring: a subject (release, service, workflow) is
scored from caller-supplied 0-100 factor readings (e.g. regression
severity, open critical findings, bottleneck count -- each engine
knows how to turn its own signals into a 0-100 factor; this service
only knows how to combine and classify them) as their simple mean,
classified into a risk level via `risk_rules`, and persisted as an
immutable point-in-time assessment."""
from __future__ import annotations

from quality_platform.config.settings import get_settings
from quality_platform.core.exceptions import ValidationError
from quality_platform.failure_analysis.risk_rules import classify_risk_level
from quality_platform.models.failure_analysis import RiskAssessmentModel
from quality_platform.repositories.registry import RepositoryRegistry


class RiskAssessmentService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def assess(self, tenant_id: str, subject_ref: str, *, factors: dict[str, float]) -> RiskAssessmentModel:
        if not factors:
            raise ValidationError("At least one risk factor is required to assess risk")
        risk_score = sum(factors.values()) / len(factors)
        risk_level = classify_risk_level(
            risk_score, high_threshold=self.settings.risk_high_threshold, critical_threshold=self.settings.risk_critical_threshold
        )
        assessment = RiskAssessmentModel(tenant_id=tenant_id, subject_ref=subject_ref, risk_score=risk_score, risk_level=risk_level.value, factors=factors)
        return await self.repos.risk_assessments.add(assessment)

    async def list_history(self, tenant_id: str, subject_ref: str, *, limit: int = 50) -> list[RiskAssessmentModel]:
        return await self.repos.risk_assessments.list_for_subject(tenant_id, subject_ref, limit=limit)

    async def latest(self, tenant_id: str, subject_ref: str) -> RiskAssessmentModel | None:
        recent = await self.list_history(tenant_id, subject_ref, limit=1)
        return recent[0] if recent else None
