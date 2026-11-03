"""API Documentation: REST/GraphQL/WebSocket/streaming endpoint
reference entries — request/response examples, an auth example, and
per-endpoint error documentation, each carrying its own version so
version history is queryable per endpoint rather than only per doc
page."""
from __future__ import annotations

from docs_platform.config.settings import get_settings
from docs_platform.core.exceptions import ApiDocEntryNotFoundError, UnsupportedApiProtocolError
from docs_platform.models.api_sdk_docs import ApiDocEntryModel
from docs_platform.repositories.registry import RepositoryRegistry


class ApiDocService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, entry_id: str) -> ApiDocEntryModel:
        entry = await self.repos.api_doc_entries.get_or_404(entry_id)
        if entry.tenant_id != tenant_id:
            raise ApiDocEntryNotFoundError(f"API doc entry '{entry_id}' not found for tenant '{tenant_id}'")
        return entry

    async def create_entry(
        self, tenant_id: str, *, protocol_type: str, path: str, method: str | None = None, summary: str = "",
        request_example: dict | None = None, response_example: dict | None = None, auth_example: str = "",
        error_docs: list | None = None, version: str = "v1",
    ) -> ApiDocEntryModel:
        if protocol_type not in self.settings.api_protocol_types:
            raise UnsupportedApiProtocolError(f"Unsupported API protocol type '{protocol_type}'")
        entry = ApiDocEntryModel(
            tenant_id=tenant_id, protocol_type=protocol_type, path=path, method=method, summary=summary,
            request_example=request_example or {}, response_example=response_example or {},
            auth_example=auth_example, error_docs=error_docs or [], version=version,
        )
        return await self.repos.api_doc_entries.add(entry)

    async def get_by_path(self, tenant_id: str, protocol_type: str, path: str, *, method: str | None = None) -> ApiDocEntryModel | None:
        return await self.repos.api_doc_entries.get_by_path(tenant_id, protocol_type, path, method)

    async def list_entries(self, tenant_id: str, *, protocol_type: str | None = None) -> list[ApiDocEntryModel]:
        return await self.repos.api_doc_entries.list_for_tenant(tenant_id, protocol_type=protocol_type)
