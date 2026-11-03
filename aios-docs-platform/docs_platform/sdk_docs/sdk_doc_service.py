"""SDK Documentation across the ten SDK/CLI targets the prompt
specifies (Python, TypeScript, Java, Go, C#, CLI, Plugin SDK,
Extension SDK, Webhook SDK, MCP SDK)."""
from __future__ import annotations

from docs_platform.config.settings import get_settings
from docs_platform.core.exceptions import SdkDocEntryNotFoundError, UnsupportedSdkLanguageError
from docs_platform.models.api_sdk_docs import SdkDocEntryModel
from docs_platform.repositories.registry import RepositoryRegistry


class SdkDocService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, entry_id: str) -> SdkDocEntryModel:
        entry = await self.repos.sdk_doc_entries.get_or_404(entry_id)
        if entry.tenant_id != tenant_id:
            raise SdkDocEntryNotFoundError(f"SDK doc entry '{entry_id}' not found for tenant '{tenant_id}'")
        return entry

    async def create_entry(
        self, tenant_id: str, *, sdk_language: str, package_ref: str, title: str, content: str = "", version: str = "v1"
    ) -> SdkDocEntryModel:
        if sdk_language not in self.settings.sdk_languages:
            raise UnsupportedSdkLanguageError(f"Unsupported SDK language '{sdk_language}'")
        entry = SdkDocEntryModel(tenant_id=tenant_id, sdk_language=sdk_language, package_ref=package_ref, title=title, content=content, version=version)
        return await self.repos.sdk_doc_entries.add(entry)

    async def list_for_language(self, tenant_id: str, sdk_language: str) -> list[SdkDocEntryModel]:
        return await self.repos.sdk_doc_entries.list_for_language(tenant_id, sdk_language)

    async def list_entries(self, tenant_id: str) -> list[SdkDocEntryModel]:
        return await self.repos.sdk_doc_entries.list_for_tenant(tenant_id)
