"""VersionService: immutable version snapshots per asset+branch, with
an optional compare-and-swap guard (via `SyncService.assert_not_stale`)
so a caller can opt into "reject my save if the asset moved on since I
last read it" the same way the Identity Platform's session-limit fix
holds a lock across the whole read-decide-write-commit sequence — here
the guard is a version-id comparison rather than a lock, appropriate
since versions are naturally append-only and don't need serialization,
just a stale-write check. Rollback creates a *new* version copying an
old one's content rather than mutating or deleting history — version
rows are never rewritten once created, so `list_versions` is always a
complete, trustworthy audit trail."""
from __future__ import annotations

import re

from collaboration_platform.config.settings import Settings, get_settings
from collaboration_platform.core.exceptions import InvalidReleaseTagError, NotFoundError
from collaboration_platform.models.version import VersionModel
from collaboration_platform.realtime.sync_service import SyncService
from collaboration_platform.repositories.registry import RepositoryRegistry


class VersionService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()
        self.sync = SyncService(repos)

    async def create_version(
        self, asset_id: str, created_by: str, content_snapshot: dict, *, branch_name: str = "main",
        change_summary: str | None = None, expected_base_version_id: str | None = "__skip__",
        is_release: bool = False, release_tag: str | None = None,
    ) -> VersionModel:
        """`expected_base_version_id="__skip__"` (the default) means the
        caller isn't opting into the CAS guard at all — pass the actual
        version id (or `None` for "no version yet") to enable it."""
        asset = await self.repos.assets.get_or_404(asset_id)
        if expected_base_version_id != "__skip__" and branch_name == "main":
            await self.sync.assert_not_stale(asset_id, expected_base_version_id)

        if is_release and release_tag is not None and not re.match(self.settings.release_tag_pattern, release_tag):
            raise InvalidReleaseTagError(f"release tag '{release_tag}' does not match pattern '{self.settings.release_tag_pattern}'")

        # Numbering + insert happen as one atomic SQL statement (see
        # `VersionRepository.add_next_version`'s docstring) rather than a
        # separate "read the max, then insert" — the latter is a proven
        # TOCTOU race under concurrent version creation for the same
        # asset+branch.
        version = await self.repos.versions.add_next_version(
            asset_id, branch_name, content_snapshot=content_snapshot, change_summary=change_summary,
            is_release=is_release, release_tag=release_tag, created_by=created_by,
        )
        if branch_name == "main":
            asset.current_version_id = version.id
            await self.repos.assets.update(asset)
        return version

    async def rollback(self, asset_id: str, target_version_id: str, *, created_by: str, branch_name: str = "main") -> VersionModel:
        target = await self.repos.versions.get(target_version_id)
        if target is None or target.asset_id != asset_id:
            raise NotFoundError(f"version '{target_version_id}' not found for asset '{asset_id}'")
        return await self.create_version(
            asset_id, created_by, dict(target.content_snapshot), branch_name=branch_name,
            change_summary=f"Rolled back to version {target.version_number}",
        )

    async def compare(self, version_id_a: str, version_id_b: str) -> dict:
        """A shallow key-level diff over the two versions' JSON
        snapshots — sufficient for arbitrary JSON content without
        assuming any particular schema; a richer structural diff is
        each owning platform's job (they know their own content shape),
        not this platform's."""
        a = await self.repos.versions.get_or_404(version_id_a)
        b = await self.repos.versions.get_or_404(version_id_b)
        keys = set(a.content_snapshot.keys()) | set(b.content_snapshot.keys())
        added, removed, changed, unchanged = {}, {}, {}, []
        for key in keys:
            in_a, in_b = key in a.content_snapshot, key in b.content_snapshot
            if in_a and not in_b:
                removed[key] = a.content_snapshot[key]
            elif in_b and not in_a:
                added[key] = b.content_snapshot[key]
            elif a.content_snapshot[key] != b.content_snapshot[key]:
                changed[key] = {"from": a.content_snapshot[key], "to": b.content_snapshot[key]}
            else:
                unchanged.append(key)
        return {"version_a": a.id, "version_b": b.id, "added": added, "removed": removed, "changed": changed, "unchanged_keys": unchanged}

    async def list_versions(self, asset_id: str, *, branch_name: str | None = None) -> list[VersionModel]:
        return await self.repos.versions.list_for_asset(asset_id, branch_name=branch_name)

    async def get_latest(self, asset_id: str, *, branch_name: str = "main") -> VersionModel | None:
        return await self.repos.versions.get_latest(asset_id, branch_name=branch_name)

    async def list_releases(self, asset_id: str) -> list[VersionModel]:
        return await self.repos.versions.list_releases(asset_id)
