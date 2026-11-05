"""Release Manager: the guarded draft -> candidate -> approved ->
released -> deprecated/yanked lifecycle every AIOS release flows
through. Every status transition is driven through the ephemeral
`Release` domain entity (loaded fresh from the ORM row, transitioned,
copied back) — the same pattern used across every other AIOS platform
for resources whose lifecycle carries real domain logic."""
from __future__ import annotations


from release_platform.config.settings import get_settings
from release_platform.core.exceptions import ConflictError, ReleaseNotFoundError, UnsupportedReleaseChannelError, ValidationError
from release_platform.domain.entities import Release
from release_platform.domain.enums import ReleaseStatus
from release_platform.models.release_versioning import ReleaseModel, VersionHistoryModel
from release_platform.release_engineering.semver_rules import InvalidSemVerError, parse_version
from release_platform.repositories.registry import RepositoryRegistry
from release_platform.clock import utc_now


class ReleaseService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, release_id: str) -> ReleaseModel:
        release = await self.repos.releases.get_or_404(release_id)
        if release.tenant_id != tenant_id:
            raise ReleaseNotFoundError(f"Release '{release_id}' not found for tenant '{tenant_id}'")
        return release

    async def create_release(
        self, tenant_id: str, *, version: str, channel: str, release_branch: str | None = None,
        build_metadata: str | None = None, changelog: str = "",
    ) -> ReleaseModel:
        if channel not in self.settings.release_channels:
            raise UnsupportedReleaseChannelError(f"Unsupported release channel '{channel}'")
        try:
            parse_version(version)
        except InvalidSemVerError as exc:
            raise ValidationError(str(exc)) from exc
        if await self.repos.releases.get_by_version(tenant_id, version) is not None:
            raise ConflictError(f"Release '{version}' already exists for tenant '{tenant_id}'")
        release = ReleaseModel(
            tenant_id=tenant_id, version=version, channel=channel, status=ReleaseStatus.DRAFT.value,
            release_branch=release_branch, build_metadata=build_metadata, changelog=changelog,
        )
        release = await self.repos.releases.add(release)
        await self.repos.version_history.add(
            VersionHistoryModel(tenant_id=tenant_id, release_id=release.id, version=version, recorded_at=utc_now(), notes="release created")
        )
        return release

    async def _apply_transition(self, tenant_id: str, release_id: str, transition_name: str) -> ReleaseModel:
        release = await self.get_or_404(tenant_id, release_id)
        entity = Release(id=release.id, tenant_id=tenant_id, version=release.version, channel=release.channel, status=ReleaseStatus(release.status))
        getattr(entity, transition_name)()
        release.status = entity.status.value
        if entity.released_at is not None:
            release.released_at = entity.released_at
        return release

    async def submit_for_candidate(self, tenant_id: str, release_id: str) -> ReleaseModel:
        return await self._apply_transition(tenant_id, release_id, "submit_for_candidate")

    async def approve(self, tenant_id: str, release_id: str) -> ReleaseModel:
        return await self._apply_transition(tenant_id, release_id, "approve")

    async def reject(self, tenant_id: str, release_id: str) -> ReleaseModel:
        return await self._apply_transition(tenant_id, release_id, "reject")

    async def revoke_approval(self, tenant_id: str, release_id: str) -> ReleaseModel:
        return await self._apply_transition(tenant_id, release_id, "revoke_approval")

    async def release(self, tenant_id: str, release_id: str) -> ReleaseModel:
        release = await self._apply_transition(tenant_id, release_id, "release")
        await self.repos.version_history.add(
            VersionHistoryModel(tenant_id=tenant_id, release_id=release.id, version=release.version, recorded_at=utc_now(), notes="released")
        )
        return release

    async def deprecate(self, tenant_id: str, release_id: str) -> ReleaseModel:
        return await self._apply_transition(tenant_id, release_id, "deprecate")

    async def yank(self, tenant_id: str, release_id: str) -> ReleaseModel:
        return await self._apply_transition(tenant_id, release_id, "yank")

    async def list_releases(self, tenant_id: str, *, channel: str | None = None, status: str | None = None) -> list[ReleaseModel]:
        return await self.repos.releases.list_for_tenant(tenant_id, channel=channel, status=status)
