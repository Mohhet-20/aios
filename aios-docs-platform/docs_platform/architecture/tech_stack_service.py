"""Architecture Portal: technology stack catalog — the "what runs
this system, and which version" reference every architecture page
and onboarding tutorial can link back to."""
from __future__ import annotations

from docs_platform.core.exceptions import ArchitectureError
from docs_platform.models.architecture import TechStackEntryModel
from docs_platform.repositories.registry import RepositoryRegistry


class TechStackService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def get_or_404(self, tenant_id: str, entry_id: str) -> TechStackEntryModel:
        entry = await self.repos.tech_stack_entries.get_or_404(entry_id)
        if entry.tenant_id != tenant_id:
            raise ArchitectureError(f"Tech stack entry '{entry_id}' not found for tenant '{tenant_id}'")
        return entry

    async def add_entry(self, tenant_id: str, *, category: str, name: str, version_info: str = "", description: str = "") -> TechStackEntryModel:
        entry = TechStackEntryModel(tenant_id=tenant_id, category=category, name=name, version_info=version_info, description=description)
        return await self.repos.tech_stack_entries.add(entry)

    async def list_entries(self, tenant_id: str, *, category: str | None = None) -> list[TechStackEntryModel]:
        return await self.repos.tech_stack_entries.list_for_tenant(tenant_id, category=category)
