"""Workflow validation run lifecycle. Status is a simple field guarded
directly here rather than through a dedicated domain entity -- the
second of the two "simple status field" resources this platform's
domain layer deliberately skipped (see `domain/entities.py`'s module
docstring). record_check() appends one of the nine workflow-
correctness dimensions' pass/fail outcome to the run's `checks` JSON
list; finish_run() tallies them into a summary and completes the run
(the job itself only fails on an execution error, mirroring
TestRunService.finish_run's "error vs. failed assertion" distinction
-- a workflow validation run that ran to completion but found failing
checks is still a *completed* run, just one with `all_passed: False`)."""
from __future__ import annotations


from quality_platform.config.settings import get_settings
from quality_platform.core.exceptions import InvalidTransitionError, WorkflowValidationError, WorkflowValidationRunNotFoundError
from quality_platform.domain.enums import JobStatus
from quality_platform.models.validation import WorkflowValidationRunModel
from quality_platform.repositories.registry import RepositoryRegistry
from quality_platform.clock import utc_now

_RUN_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.QUEUED: {JobStatus.RUNNING},
    JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED},
    JobStatus.COMPLETED: set(),
    JobStatus.FAILED: set(),
}


class WorkflowValidationRunService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, run_id: str) -> WorkflowValidationRunModel:
        run = await self.repos.workflow_validation_runs.get_or_404(run_id)
        if run.tenant_id != tenant_id:
            raise WorkflowValidationRunNotFoundError(f"Workflow validation run '{run_id}' not found for tenant '{tenant_id}'")
        return run

    async def request_run(self, tenant_id: str, *, workflow_ref: str) -> WorkflowValidationRunModel:
        run = WorkflowValidationRunModel(tenant_id=tenant_id, workflow_ref=workflow_ref, status=JobStatus.QUEUED.value)
        return await self.repos.workflow_validation_runs.add(run)

    async def _transition(self, tenant_id: str, run_id: str, target: JobStatus) -> WorkflowValidationRunModel:
        run = await self.get_or_404(tenant_id, run_id)
        current = JobStatus(run.status)
        if target not in _RUN_TRANSITIONS.get(current, set()):
            raise InvalidTransitionError(f"WorkflowValidationRun '{run_id}' cannot transition from {current.value} to {target.value}")
        run.status = target.value
        return run

    async def start(self, tenant_id: str, run_id: str) -> WorkflowValidationRunModel:
        run = await self._transition(tenant_id, run_id, JobStatus.RUNNING)
        return await self.repos.workflow_validation_runs.update(run)

    async def fail(self, tenant_id: str, run_id: str, *, error: str) -> WorkflowValidationRunModel:
        run = await self._transition(tenant_id, run_id, JobStatus.FAILED)
        run.error = error
        run.completed_at = utc_now()
        return await self.repos.workflow_validation_runs.update(run)

    async def record_check(self, tenant_id: str, run_id: str, *, check: str, passed: bool, details: str = "") -> WorkflowValidationRunModel:
        if check not in self.settings.workflow_validation_checks:
            raise WorkflowValidationError(f"Unsupported workflow validation check '{check}'")
        run = await self.get_or_404(tenant_id, run_id)
        checks = list(run.checks)
        checks.append({"check": check, "passed": passed, "details": details})
        run.checks = checks
        return await self.repos.workflow_validation_runs.update(run)

    async def finish_run(self, tenant_id: str, run_id: str) -> WorkflowValidationRunModel:
        run = await self.get_or_404(tenant_id, run_id)
        checks = run.checks
        failed = [c for c in checks if not c["passed"]]
        result = {"total_checks": len(checks), "passed_checks": len(checks) - len(failed), "failed_checks": [c["check"] for c in failed], "all_passed": not failed}
        transitioned = await self._transition(tenant_id, run_id, JobStatus.COMPLETED)
        transitioned.result = result
        transitioned.completed_at = utc_now()
        return await self.repos.workflow_validation_runs.update(transitioned)

    async def list_runs(self, tenant_id: str, *, workflow_ref: str | None = None, limit: int = 100) -> list[WorkflowValidationRunModel]:
        return await self.repos.workflow_validation_runs.list_for_tenant(tenant_id, workflow_ref=workflow_ref, limit=limit)
