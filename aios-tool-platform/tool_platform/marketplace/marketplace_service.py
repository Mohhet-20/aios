"""MarketplaceService: the read/browse/discover side of the Plugin
Platform — searching published listings by category/tag/query, and
surfacing the install-count popularity signal that
`installation_service.py` increments. Kept as its own module (rather
than folded into `registry_service.py`) because "browse the
marketplace" and "publish/version a listing" are different callers with
different permission needs (any user vs. a plugin author/admin)."""
from __future__ import annotations

from tool_platform.models.plugin import PluginModel
from tool_platform.repositories.registry import RepositoryRegistry


class MarketplaceService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def search(self, *, category: str | None = None, tag: str | None = None, query: str | None = None) -> list[PluginModel]:
        return await self.repos.plugins.search(category=category, tag=tag, query=query)

    async def get_listing(self, plugin_id: str) -> PluginModel:
        return await self.repos.plugins.get_or_404(plugin_id)

    async def most_installed(self, *, limit: int = 10) -> list[PluginModel]:
        listings = await self.repos.plugins.search()
        return sorted(listings, key=lambda p: p.install_count, reverse=True)[:limit]
