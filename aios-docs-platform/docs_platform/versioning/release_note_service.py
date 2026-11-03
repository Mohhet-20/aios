"""Release Notes: entries across five kinds (feature, fix, breaking
change, deprecation, security), grouped by version label so a release
page can render "everything that shipped in v1.4" in one query."""
from __future__ import annotations

from docs_platform.core.exceptions import ValidationError
from docs_platform.domain.enums import ReleaseNoteKind
from docs_platform.models.versioning import ReleaseNoteModel
from docs_platform.repositories.registry import RepositoryRegistry

_VALID_KINDS = {k.value for k in ReleaseNoteKind}


class ReleaseNoteService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_note(self, tenant_id: str, *, version_label: str, title: str, content: str = "", kind: str = "feature") -> ReleaseNoteModel:
        if kind not in _VALID_KINDS:
            raise ValidationError(f"Unsupported release note kind '{kind}'")
        note = ReleaseNoteModel(tenant_id=tenant_id, version_label=version_label, title=title, content=content, kind=kind)
        return await self.repos.release_notes.add(note)

    async def list_notes(self, tenant_id: str, *, version_label: str | None = None, limit: int = 100) -> list[ReleaseNoteModel]:
        return await self.repos.release_notes.list_for_tenant(tenant_id, version_label=version_label, limit=limit)
