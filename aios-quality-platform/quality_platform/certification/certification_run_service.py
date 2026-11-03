"""Release certification job lifecycle: request_run() enqueues a
certification attempt for a release, start()/complete()/fail() drive
the guarded queued -> running -> completed/failed transitions on the
domain-level `CertificationRun` entity, and certify() is the
convenience orchestrator that combines whichever
quality/reliability/security/performance/AI-quality scores the caller
supplies into a weighted overall score and deployment decision via
`certification_rules`, then completes the run with the full report
attached."""
from __future__ import annotations


from quality_platform.certification.certification_rules import compute_overall_score, decide_certification
from quality_platform.config.settings import get_settings
from quality_platform.core.exceptions import CertificationRunNotFoundError, InvalidTransitionError
from quality_platform.domain.entities import CertificationRun
from quality_platform.domain.enums import JobStatus
from quality_platform.models.certification import CertificationRunModel
from quality_platform.repositories.registry import RepositoryRegistry
from quality_platform.clock import utc_now


class CertificationRunService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, run_id: str) -> CertificationRunModel:
        run = await self.repos.certification_runs.get_or_404(run_id)
        if run.tenant_id != tenant_id:
            raise CertificationRunNotFoundError(f"Certification run '{run_id}' not found for tenant '{tenant_id}'")
        return run

    async def request_run(self, tenant_id: str, *, release_ref: str) -> CertificationRunModel:
        run = CertificationRunModel(tenant_id=tenant_id, release_ref=release_ref, status=JobStatus.QUEUED.value)
        return await self.repos.certification_runs.add(run)

    async def _apply_transition(self, tenant_id: str, run_id: str, transition_name: str) -> CertificationRunModel:
        run = await self.get_or_404(tenant_id, run_id)
        entity = CertificationRun(id=run.id, status=JobStatus(run.status))
        try:
            getattr(entity, transition_name)()
        except InvalidTransitionError:
            raise
        run.status = entity.status.value
        return run

    async def start(self, tenant_id: str, run_id: str) -> CertificationRunModel:
        run = await self._apply_transition(tenant_id, run_id, "start")
        return await self.repos.certification_runs.update(run)

    async def complete(
        self, tenant_id: str, run_id: str, *,
        quality_score: float | None, reliability_score: float | None, security_score: float | None,
        performance_score: float | None, ai_quality_score: float | None, overall_score: float, decision: str, report: dict,
    ) -> CertificationRunModel:
        run = await self._apply_transition(tenant_id, run_id, "complete")
        run.quality_score = quality_score
        run.reliability_score = reliability_score
        run.security_score = security_score
        run.performance_score = performance_score
        run.ai_quality_score = ai_quality_score
        run.overall_score = overall_score
        run.decision = decision
        run.report = report
        run.completed_at = utc_now()
        return await self.repos.certification_runs.update(run)

    async def fail(self, tenant_id: str, run_id: str, *, error: str) -> CertificationRunModel:
        run = await self._apply_transition(tenant_id, run_id, "fail")
        run.error = error
        run.completed_at = utc_now()
        return await self.repos.certification_runs.update(run)

    async def certify(
        self, tenant_id: str, run_id: str, *,
        quality_score: float | None = None, reliability_score: float | None = None, security_score: float | None = None,
        performance_score: float | None = None, ai_quality_score: float | None = None,
    ) -> CertificationRunModel:
        await self.start(tenant_id, run_id)

        scores = {
            "quality": quality_score, "reliability": reliability_score, "security": security_score,
            "performance": performance_score, "ai_quality": ai_quality_score,
        }
        supplied = {k: v for k, v in scores.items() if v is not None}
        if not supplied:
            return await self.fail(tenant_id, run_id, error="No category scores supplied for certification")

        overall = compute_overall_score(supplied, self.settings.certification_score_weights)
        decision = decide_certification(overall, min_score_for_approval=self.settings.certification_min_score_for_approval)
        report = {
            "scores": supplied, "overall_score": overall, "decision": decision.value,
            "weights_used": {k: w for k, w in self.settings.certification_score_weights.items() if k in supplied},
        }
        return await self.complete(
            tenant_id, run_id, quality_score=quality_score, reliability_score=reliability_score, security_score=security_score,
            performance_score=performance_score, ai_quality_score=ai_quality_score, overall_score=overall,
            decision=decision.value, report=report,
        )

    async def list_for_release(self, tenant_id: str, release_ref: str, *, limit: int = 50) -> list[CertificationRunModel]:
        return await self.repos.certification_runs.list_for_release(tenant_id, release_ref, limit=limit)
