"""Automated documentation generation: a guarded job lifecycle across
the eight generation types the prompt specifies (API docs, schema
docs, config docs, SDK docs, changelogs, dependency reports,
architecture reports, code reference). This service is the control
plane for automation — it does not itself introspect a live codebase
or database schema (that's genuinely out of scope for a docs-platform
control plane, the same disclosed boundary every prior AIOS platform
draws around "we orchestrate, we don't reimplement the underlying
tool"). `run_job()` is the convenience orchestrator most callers want:
it starts the job, hands control to a caller-supplied async generator
function, and completes the job with whatever result payload that
function returns — or fails it if the function raises."""
from __future__ import annotations

from collections.abc import Awaitable, Callable

from typing import Any

from docs_platform.config.settings import get_settings
from docs_platform.core.exceptions import GenerationJobNotFoundError, InvalidTransitionError, UnsupportedGenerationJobTypeError
from docs_platform.domain.entities import GenerationJob
from docs_platform.domain.enums import JobStatus
from docs_platform.models.api_sdk_docs import GenerationJobModel
from docs_platform.repositories.registry import RepositoryRegistry
from docs_platform.clock import utc_now


class GenerationJobService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, job_id: str) -> GenerationJobModel:
        job = await self.repos.generation_jobs.get_or_404(job_id)
        if job.tenant_id != tenant_id:
            raise GenerationJobNotFoundError(f"Generation job '{job_id}' not found for tenant '{tenant_id}'")
        return job

    async def request_job(self, tenant_id: str, *, job_type: str, target_ref: str, config: dict | None = None) -> GenerationJobModel:
        if job_type not in self.settings.generation_job_types:
            raise UnsupportedGenerationJobTypeError(f"Unsupported generation job type '{job_type}'")
        job = GenerationJobModel(tenant_id=tenant_id, job_type=job_type, target_ref=target_ref, status=JobStatus.QUEUED.value, config=config or {})
        return await self.repos.generation_jobs.add(job)

    async def _apply_transition(self, tenant_id: str, job_id: str, transition_name: str) -> GenerationJobModel:
        job = await self.get_or_404(tenant_id, job_id)
        entity = GenerationJob(id=job.id, status=JobStatus(job.status))
        try:
            getattr(entity, transition_name)()
        except InvalidTransitionError:
            raise
        job.status = entity.status.value
        return job

    async def start(self, tenant_id: str, job_id: str) -> GenerationJobModel:
        job = await self._apply_transition(tenant_id, job_id, "start")
        return await self.repos.generation_jobs.update(job)

    async def complete(self, tenant_id: str, job_id: str, *, result: dict) -> GenerationJobModel:
        job = await self._apply_transition(tenant_id, job_id, "complete")
        job.result = result
        job.completed_at = utc_now()
        return await self.repos.generation_jobs.update(job)

    async def fail(self, tenant_id: str, job_id: str, *, error: str) -> GenerationJobModel:
        job = await self._apply_transition(tenant_id, job_id, "fail")
        job.error = error
        job.completed_at = utc_now()
        return await self.repos.generation_jobs.update(job)

    async def run_job(
        self, tenant_id: str, job_id: str, generator: Callable[[GenerationJobModel], Awaitable[dict[str, Any]]] | None = None
    ) -> GenerationJobModel:
        await self.start(tenant_id, job_id)
        job = await self.get_or_404(tenant_id, job_id)
        try:
            if generator is not None:
                result = await generator(job)
            else:
                # No generator supplied: produce a minimal, honest
                # result shape rather than pretending to have actually
                # introspected anything.
                result = {"job_type": job.job_type, "target_ref": job.target_ref, "generated": False, "note": "no generator function supplied"}
        except Exception as exc:  # noqa: BLE001 - any generator failure should fail the job, not crash the caller
            return await self.fail(tenant_id, job_id, error=str(exc))
        return await self.complete(tenant_id, job_id, result=result)

    async def list_jobs(self, tenant_id: str, *, job_type: str | None = None, limit: int = 100) -> list[GenerationJobModel]:
        return await self.repos.generation_jobs.list_for_tenant(tenant_id, job_type=job_type, limit=limit)
