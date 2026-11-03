"""Version Manager: version history (an append-only log the release
service writes to on creation and on release) and the compatibility
matrix — which component versions a given platform version is
compatible with, queried via the pure semver comparison helpers."""
from __future__ import annotations

from release_platform.models.release_versioning import CompatibilityEntryModel, VersionHistoryModel
from release_platform.release_engineering.semver_rules import is_compatible
from release_platform.repositories.registry import RepositoryRegistry


class VersionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def list_history(self, tenant_id: str, release_id: str) -> list[VersionHistoryModel]:
        return await self.repos.version_history.list_for_release(tenant_id, release_id)

    async def add_compatibility_entry(
        self, tenant_id: str, *, version: str, component_ref: str, compatible_from: str, compatible_to: str | None = None
    ) -> CompatibilityEntryModel:
        entry = CompatibilityEntryModel(
            tenant_id=tenant_id, version=version, component_ref=component_ref,
            compatible_from=compatible_from, compatible_to=compatible_to,
        )
        return await self.repos.compatibility_entries.add(entry)

    async def list_compatibility(self, tenant_id: str, version: str) -> list[CompatibilityEntryModel]:
        return await self.repos.compatibility_entries.list_for_version(tenant_id, version)

    async def check_compatible(self, tenant_id: str, version: str, component_ref: str, candidate_version: str) -> bool:
        entries = await self.list_compatibility(tenant_id, version)
        matching = [e for e in entries if e.component_ref == component_ref]
        if not matching:
            return False
        return any(is_compatible(candidate_version, compatible_from=e.compatible_from, compatible_to=e.compatible_to) for e in matching)
