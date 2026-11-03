"""Doc space management. `register_space` is a get-or-create upsert
keyed on (tenant_id, key) behind a commit-spanning `asyncio.Lock` —
the same pattern established across every prior AIOS platform, with
the mid-lock commit needed so a waiting caller's read can't observe a
still-uncommitted insert from a separate DB connection."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from docs_platform.config.settings import get_settings
from docs_platform.core.exceptions import DocSpaceNotFoundError, UnsupportedDocTypeError
from docs_platform.models.documentation import DocSpaceModel
from docs_platform.repositories.registry import RepositoryRegistry


class DocSpaceService:
    _register_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    def _validate_doc_type(self, doc_type: str) -> None:
        if doc_type not in self.settings.doc_types:
            raise UnsupportedDocTypeError(f"Unsupported doc type '{doc_type}'")

    async def get_or_404(self, tenant_id: str, space_id: str) -> DocSpaceModel:
        space = await self.repos.doc_spaces.get_or_404(space_id)
        if space.tenant_id != tenant_id:
            raise DocSpaceNotFoundError(f"Doc space '{space_id}' not found for tenant '{tenant_id}'")
        return space

    async def register_space(self, tenant_id: str, *, key: str, name: str, doc_type: str, description: str | None = None) -> DocSpaceModel:
        self._validate_doc_type(doc_type)
        lock_key = f"{tenant_id}:{key}"
        async with self._register_locks[lock_key]:
            existing = await self.repos.doc_spaces.get_by_key(tenant_id, key)
            if existing is not None:
                return existing
            space = DocSpaceModel(tenant_id=tenant_id, key=key, name=name, doc_type=doc_type, description=description)
            space = await self.repos.doc_spaces.add(space)
            await self.repos.session.commit()
            return space

    async def list_spaces(self, tenant_id: str, *, doc_type: str | None = None) -> list[DocSpaceModel]:
        return await self.repos.doc_spaces.list_for_tenant(tenant_id, doc_type=doc_type)
