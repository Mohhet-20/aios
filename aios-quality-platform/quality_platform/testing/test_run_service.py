"""Test run execution lifecycle: request_run() enqueues a run against
a suite, start()/complete()/fail() drive the guarded queued -> running
-> completed/failed transitions on the domain-level `TestRun` entity
while persisting each transition onto the ORM row, record_result()
appends a per-case result (re-classifying it as "flaky" when the
case's recent history crosses `test_run_flaky_threshold`), and
finish_run() is the convenience orchestrator that tallies results into
a summary and completes (or fails, if any result errored) the run."""
from __future__ import annotations


from quality_platform.config.settings import get_settings
from quality_platform.core.exceptions import InvalidTransitionError, TestRunNotFoundError, ValidationError
from quality_platform.domain.entities import TestRun
from quality_platform.domain.enums import JobStatus
from quality_platform.models.testing import TestCaseResultModel, TestRunModel
from quality_platform.repositories.registry import RepositoryRegistry
from quality_platform.testing.flaky_detection import is_flaky
from quality_platform.testing.test_suite_service import TestSuiteService
from quality_platform.clock import utc_now


class TestRunService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()
        self.suites = TestSuiteService(repos)

    async def get_or_404(self, tenant_id: str, run_id: str) -> TestRunModel:
        run = await self.repos.test_runs.get_or_404(run_id)
        if run.tenant_id != tenant_id:
            raise TestRunNotFoundError(f"Test run '{run_id}' not found for tenant '{tenant_id}'")
        return run

    async def request_run(self, tenant_id: str, suite_id: str, *, triggered_by: str | None = None) -> TestRunModel:
        suite = await self.suites.get_suite_or_404(tenant_id, suite_id)
        if suite.status != "active":
            raise ValidationError(f"Test suite '{suite_id}' is not active")
        run = TestRunModel(tenant_id=tenant_id, suite_id=suite_id, status=JobStatus.QUEUED.value, triggered_by=triggered_by)
        return await self.repos.test_runs.add(run)

    async def _apply_transition(self, tenant_id: str, run_id: str, transition_name: str) -> TestRunModel:
        run = await self.get_or_404(tenant_id, run_id)
        entity = TestRun(id=run.id, status=JobStatus(run.status))
        try:
            getattr(entity, transition_name)()
        except InvalidTransitionError:
            raise
        run.status = entity.status.value
        return run

    async def start(self, tenant_id: str, run_id: str) -> TestRunModel:
        run = await self._apply_transition(tenant_id, run_id, "start")
        return await self.repos.test_runs.update(run)

    async def complete(self, tenant_id: str, run_id: str, *, summary: dict) -> TestRunModel:
        run = await self._apply_transition(tenant_id, run_id, "complete")
        run.summary = summary
        run.completed_at = utc_now()
        return await self.repos.test_runs.update(run)

    async def fail(self, tenant_id: str, run_id: str, *, error: str) -> TestRunModel:
        run = await self._apply_transition(tenant_id, run_id, "fail")
        run.error = error
        run.completed_at = utc_now()
        return await self.repos.test_runs.update(run)

    async def record_result(
        self, tenant_id: str, run_id: str, test_case_id: str, *, result: str, duration_ms: float = 0.0, message: str | None = None
    ) -> TestCaseResultModel:
        await self.get_or_404(tenant_id, run_id)
        await self.suites.get_case_or_404(tenant_id, test_case_id)

        if result in ("passed", "failed"):
            history = await self.repos.test_case_results.list_for_case(
                tenant_id, test_case_id, limit=self.settings.test_run_history_window
            )
            recent = [result] + [r.result for r in history]
            if is_flaky(recent, threshold=self.settings.test_run_flaky_threshold):
                result = "flaky"

        record = TestCaseResultModel(
            tenant_id=tenant_id, test_run_id=run_id, test_case_id=test_case_id,
            result=result, duration_ms=duration_ms, message=message,
        )
        return await self.repos.test_case_results.add(record)

    async def finish_run(self, tenant_id: str, run_id: str) -> TestRunModel:
        """Tallies every recorded result for this run into a summary
        and completes the run — fails it instead if any case errored,
        since an execution-level error (not just a failed assertion)
        means the run itself couldn't be trusted."""
        results = await self.repos.test_case_results.list_for_run(tenant_id, run_id)
        summary: dict[str, int] = {"passed": 0, "failed": 0, "skipped": 0, "flaky": 0, "error": 0, "total": len(results)}
        for r in results:
            summary[r.result] = summary.get(r.result, 0) + 1

        if summary["error"] > 0:
            return await self.fail(tenant_id, run_id, error=f"{summary['error']} test case(s) errored")
        return await self.complete(tenant_id, run_id, summary=summary)

    async def is_case_flaky(self, tenant_id: str, test_case_id: str) -> bool:
        await self.suites.get_case_or_404(tenant_id, test_case_id)
        history = await self.repos.test_case_results.list_for_case(
            tenant_id, test_case_id, limit=self.settings.test_run_history_window
        )
        return is_flaky([r.result for r in history], threshold=self.settings.test_run_flaky_threshold)

    async def list_runs(self, tenant_id: str, suite_id: str, *, limit: int = 100) -> list[TestRunModel]:
        await self.suites.get_suite_or_404(tenant_id, suite_id)
        return await self.repos.test_runs.list_for_suite(tenant_id, suite_id, limit=limit)
