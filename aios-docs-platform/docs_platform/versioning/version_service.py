"""Versioned Documentation: read-side access to the immutable
content snapshots `DocPageService` writes on every draft edit
(version 1 at creation, version N+1 on each `update_content` call),
plus a diff between any two of a page's versions."""
from __future__ import annotations

from docs_platform.core.exceptions import DocVersionNotFoundError
from docs_platform.models.versioning import DocVersionModel
from docs_platform.repositories.registry import RepositoryRegistry
from docs_platform.versioning.diff_rules import compute_diff


class DocVersionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def list_versions(self, tenant_id: str, page_id: str) -> list[DocVersionModel]:
        return await self.repos.doc_versions.list_for_page(tenant_id, page_id)

    async def get_version(self, tenant_id: str, page_id: str, version_number: int) -> DocVersionModel:
        version = await self.repos.doc_versions.get_version(tenant_id, page_id, version_number)
        if version is None:
            raise DocVersionNotFoundError(f"Version {version_number} of page '{page_id}' not found for tenant '{tenant_id}'")
        return version

    async def diff(self, tenant_id: str, page_id: str, *, from_version: int, to_version: int) -> list[str]:
        old = await self.get_version(tenant_id, page_id, from_version)
        new = await self.get_version(tenant_id, page_id, to_version)
        return compute_diff(old.content_snapshot, new.content_snapshot, from_label=f"v{from_version}", to_label=f"v{to_version}")
