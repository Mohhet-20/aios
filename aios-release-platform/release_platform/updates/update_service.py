"""Update Infrastructure: update jobs across the 7 declared types
(automatic, manual, scheduled, delta, patch, offline, rollback),
guarded by an inline `_UPDATE_TRANSITIONS` dict rather than a
dedicated domain entity — a "simple status field" resource in the
same sense as every other AIOS platform's status-only resources,
since an update job's lifecycle carries no logic beyond the sequence
of states themselves. Version-compatibility checking is delegated to
`release_engineering.VersionService`'s compatibility matrix rather
than reimplemented here."""
from __future__ import annotations

from datetime import datetime

from release_platform.config.settings import get_settings
from release_platform.core.exceptions import (
    InvalidTransitionError,
    UnsupportedUpdateTypeError,
    UpdateJobNotFoundError,
    VersionCompatibilityError,
)
from release_platform.domain.enums import JobStatus
from release_platform.models.update import UpdateJobModel
from release_platform.release_engineering.semver_rules import InvalidSemVerError, parse_version
from release_platform.release_engineering.version_service import VersionService
from release_platform.repositories.registry import RepositoryRegistry
from release_platform.clock import utc_now

_UPDATE_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"downloading", "failed"},
    "downloading": {"applying", "failed"},
    "applying": {"applied", "failed"},
    "applied": {"rolled_back"},
    "failed": set(),
    "rolled_back": set(),
}


class UpdateJobService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()
        self.versions = VersionService(repos)

    async def get_or_404(self, tenant_id: str, job_id: str) -> UpdateJobModel:
        job = await self.repos.update_jobs.get_or_404(job_id)
        if job.tenant_id != tenant_id:
            raise UpdateJobNotFoundError(f"Update job '{job_id}' not found for tenant '{tenant_id}'")
        return job

    async def schedule_update(
        self, tenant_id: str, *, target_ref: str, update_type: str, to_version: str,
        from_version: str | None = None, scheduled_at: datetime | None = None,
    ) -> UpdateJobModel:
        if update_type not in self.settings.update_types:
            raise UnsupportedUpdateTypeError(f"Unsupported update type '{update_type}'")
        try:
            parse_version(to_version)
        except InvalidSemVerError as exc:
            raise UnsupportedUpdateTypeError(str(exc)) from exc
        job = UpdateJobModel(
            tenant_id=tenant_id, target_ref=target_ref, update_type=update_type, to_version=to_version,
            from_version=from_version, status=JobStatus.QUEUED.value, scheduled_at=scheduled_at,
        )
        return await self.repos.update_jobs.add(job)

    async def _transition(self, tenant_id: str, job_id: str, target: str) -> UpdateJobModel:
        job = await self.get_or_404(tenant_id, job_id)
        if target not in _UPDATE_TRANSITIONS.get(job.status, set()):
            raise InvalidTransitionError(f"Cannot transition update job from '{job.status}' to '{target}'")
        job.status = target
        return job

    async def start_download(self, tenant_id: str, job_id: str) -> UpdateJobModel:
        return await self._transition(tenant_id, job_id, "downloading")

    async def begin_apply(self, tenant_id: str, job_id: str) -> UpdateJobModel:
        return await self._transition(tenant_id, job_id, "applying")

    async def mark_applied(self, tenant_id: str, job_id: str) -> UpdateJobModel:
        job = await self._transition(tenant_id, job_id, "applied")
        job.applied_at = utc_now()
        return job

    async def fail(self, tenant_id: str, job_id: str, *, reason: str) -> UpdateJobModel:
        job = await self._transition(tenant_id, job_id, "failed")
        job.failure_reason = reason
        return job

    async def mark_rolled_back(self, tenant_id: str, job_id: str) -> UpdateJobModel:
        return await self._transition(tenant_id, job_id, "rolled_back")

    async def check_version_compatibility(self, tenant_id: str, *, platform_version: str, component_ref: str, candidate_version: str) -> None:
        compatible = await self.versions.check_compatible(tenant_id, platform_version, component_ref, candidate_version)
        if not compatible:
            raise VersionCompatibilityError(
                f"'{candidate_version}' is not compatible with platform version '{platform_version}' for component '{component_ref}'"
            )

    async def list_for_target(self, tenant_id: str, target_ref: str, *, limit: int = 100) -> list[UpdateJobModel]:
        return await self.repos.update_jobs.list_for_target(tenant_id, target_ref, limit=limit)
