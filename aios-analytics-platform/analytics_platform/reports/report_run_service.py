"""Report run lifecycle: request_run() enqueues a run against an
active definition, start()/complete()/fail() drive the guarded queued
-> generating -> completed/failed transitions on the domain-level
`ReportRun` entity (entities.py) while persisting each transition onto
the ORM row, and generate() is the convenience orchestrator most
callers want — it drives start(), delegates content assembly to
`ReportGeneratorService`, then complete()s or fail()s depending on the
outcome. Exposing the individual steps (not just the all-in-one
`generate()`) matters for callers that run report generation out of
process: a worker can `start()` a run the instant it picks it up, then
`complete()`/`fail()` only once the real work is done."""
from __future__ import annotations


from analytics_platform.core.exceptions import InvalidTransitionError, ReportGenerationFailedError, ReportNotFoundError, ValidationError
from analytics_platform.domain.entities import ReportRun
from analytics_platform.domain.enums import ReportRunStatus
from analytics_platform.models.reports import ReportRunModel
from analytics_platform.reports.report_definition_service import ReportDefinitionService
from analytics_platform.reports.report_generator import ReportGeneratorService
from analytics_platform.repositories.registry import RepositoryRegistry
from analytics_platform.clock import utc_now


class ReportRunService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.definitions = ReportDefinitionService(repos)
        self.generator = ReportGeneratorService(repos)

    async def get_or_404(self, tenant_id: str, run_id: str) -> ReportRunModel:
        run = await self.repos.report_runs.get_or_404(run_id)
        if run.tenant_id != tenant_id:
            raise ReportNotFoundError(f"Report run '{run_id}' not found for tenant '{tenant_id}'")
        return run

    async def request_run(self, tenant_id: str, report_definition_id: str) -> ReportRunModel:
        definition = await self.definitions.get_or_404(tenant_id, report_definition_id)
        if definition.status != "active":
            raise ValidationError(f"Report definition '{report_definition_id}' is not active")
        run = ReportRunModel(tenant_id=tenant_id, report_definition_id=definition.id, status=ReportRunStatus.QUEUED.value)
        return await self.repos.report_runs.add(run)

    async def _apply_transition(self, tenant_id: str, run_id: str, transition_name: str) -> tuple[ReportRunModel, ReportRun]:
        run = await self.get_or_404(tenant_id, run_id)
        entity = ReportRun(id=run.id, status=ReportRunStatus(run.status))
        try:
            getattr(entity, transition_name)()
        except InvalidTransitionError as exc:
            raise ReportGenerationFailedError(str(exc)) from exc
        run.status = entity.status.value
        return run, entity

    async def start(self, tenant_id: str, run_id: str) -> ReportRunModel:
        run, _ = await self._apply_transition(tenant_id, run_id, "start")
        return await self.repos.report_runs.update(run)

    async def complete(self, tenant_id: str, run_id: str, *, output: dict) -> ReportRunModel:
        run, _ = await self._apply_transition(tenant_id, run_id, "complete")
        run.output = output
        run.completed_at = utc_now()
        return await self.repos.report_runs.update(run)

    async def fail(self, tenant_id: str, run_id: str, *, error: str) -> ReportRunModel:
        run, _ = await self._apply_transition(tenant_id, run_id, "fail")
        run.error = error
        run.completed_at = utc_now()
        return await self.repos.report_runs.update(run)

    async def generate(self, tenant_id: str, run_id: str) -> ReportRunModel:
        await self.start(tenant_id, run_id)

        run = await self.get_or_404(tenant_id, run_id)
        definition = await self.definitions.get_or_404(tenant_id, run.report_definition_id)
        try:
            payload = await self.generator.build_payload(tenant_id, report_type=definition.report_type, config=definition.config)
        except Exception as exc:  # noqa: BLE001 - genuinely any assembly failure should fail the run, not crash the caller
            return await self.fail(tenant_id, run_id, error=str(exc))

        return await self.complete(tenant_id, run_id, output=payload)

    async def list_for_definition(self, tenant_id: str, report_definition_id: str, *, limit: int = 100) -> list[ReportRunModel]:
        return await self.repos.report_runs.list_for_definition(tenant_id, report_definition_id, limit=limit)
