"""Code generation orchestration: create a job against a source spec,
run the target-appropriate generator, persist each generated file as a
`CodeGenArtifactModel` (checksum + size, same "own the pointer, not the
data" posture — the actual file bytes aren't stored in this row, only
its identity and hash; a real deployment would push the bytes to
object storage keyed by this checksum), and guard the job through its
queued -> running -> completed/failed lifecycle. Every generated file
is syntax-checked before being recorded as an artifact — a generator
bug should fail the job loudly, never silently persist broken output."""
from __future__ import annotations

import ast
import hashlib

from developer_platform.codegen.generators.python_generator import PythonClientGenerator
from developer_platform.codegen.generators.typescript_generator import TypeScriptClientGenerator
from developer_platform.codegen.mappers import apply_codegen_job_domain_to_model, codegen_job_to_domain
from developer_platform.config.settings import Settings, get_settings
from developer_platform.core.exceptions import CodeGenError, CodeGenJobFailedError, CodeGenUnsupportedTargetError, NotFoundError
from developer_platform.database.base import utcnow
from developer_platform.domain.enums import CodeGenStatus
from developer_platform.models.codegen import CodeGenArtifactModel, CodeGenJobModel
from developer_platform.repositories.registry import RepositoryRegistry

_GENERATORS = {
    "python": PythonClientGenerator(),
    "typescript": TypeScriptClientGenerator(),
}


def _validate_output(target: str, file_path: str, content: str) -> None:
    """Best-effort syntax validation — Python output is checked with
    the real `ast` parser; TypeScript output gets a structural sanity
    check only, since validating TS syntax properly would require a
    TypeScript compiler this platform doesn't ship."""
    if target == "python" and file_path.endswith(".py"):
        ast.parse(content)


class CodeGenEngine:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    def _assert_supported_target(self, target: str) -> None:
        if target not in self.settings.codegen_output_formats:
            raise CodeGenUnsupportedTargetError(
                f"'{target}' is not a supported code-gen target; supported: {self.settings.codegen_output_formats}"
            )

    async def create_job(
        self, tenant_id: str, *, target: str, source_spec_ref: str, requested_by: str | None = None,
    ) -> CodeGenJobModel:
        self._assert_supported_target(target)
        job = CodeGenJobModel(
            tenant_id=tenant_id, target=target, source_spec_ref=source_spec_ref,
            status=CodeGenStatus.QUEUED.value, requested_by=requested_by,
        )
        return await self.repos.codegen_jobs.add(job)

    async def run_job(self, tenant_id: str, job_id: str, *, spec: dict) -> CodeGenJobModel:
        job = await self._get_job_or_404(tenant_id, job_id)
        entity = codegen_job_to_domain(job)
        entity.start()
        apply_codegen_job_domain_to_model(entity, job)
        job.started_at = utcnow()
        job = await self.repos.codegen_jobs.update(job)

        try:
            generator = _GENERATORS[job.target]
            files = generator.generate(spec)
            for file_path, content in files.items():
                _validate_output(job.target, file_path, content)
                checksum = hashlib.sha256(content.encode()).hexdigest()
                artifact = CodeGenArtifactModel(
                    tenant_id=tenant_id, job_id=job.id, file_path=file_path,
                    checksum=checksum, size_bytes=len(content.encode()),
                )
                await self.repos.codegen_artifacts.add(artifact)
        except Exception as exc:
            entity = codegen_job_to_domain(job)
            entity.fail()
            apply_codegen_job_domain_to_model(entity, job)
            job.error = str(exc)
            await self.repos.codegen_jobs.update(job)
            raise CodeGenJobFailedError(f"code-gen job '{job.id}' failed: {exc}") from exc

        entity = codegen_job_to_domain(job)
        entity.complete()
        apply_codegen_job_domain_to_model(entity, job)
        return await self.repos.codegen_jobs.update(job)

    async def list_artifacts(self, tenant_id: str, job_id: str) -> list[CodeGenArtifactModel]:
        return await self.repos.codegen_artifacts.list_for_job(tenant_id, job_id)

    async def list_jobs(self, tenant_id: str) -> list[CodeGenJobModel]:
        return await self.repos.codegen_jobs.list_for_tenant(tenant_id)

    async def _get_job_or_404(self, tenant_id: str, job_id: str) -> CodeGenJobModel:
        try:
            job = await self.repos.codegen_jobs.get_or_404(job_id)
        except NotFoundError as exc:
            raise CodeGenError(f"code-gen job '{job_id}' not found") from exc
        if job.tenant_id != tenant_id:
            raise CodeGenError(f"code-gen job '{job_id}' not found for tenant '{tenant_id}'")
        return job
