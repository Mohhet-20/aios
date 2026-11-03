"""Plugin marketplace listing lifecycle: submit for review -> approve
or reject -> list publicly (or auto-list when
`plugin_marketplace_requires_review` is off). Separate from the
version-signing lifecycle in `lifecycle_service.py` — a plugin can
have a signed, published version without ever being marketplace-listed
(private/internal plugins), which is why this is its own service over
its own table rather than folded into `PluginLifecycleService`."""
from __future__ import annotations

from developer_platform.config.settings import Settings, get_settings
from developer_platform.core.exceptions import ValidationError
from developer_platform.database.base import utcnow
from developer_platform.domain.enums import MarketplaceReviewStatus
from developer_platform.models.plugins import PluginMarketplaceListingModel
from developer_platform.repositories.registry import RepositoryRegistry


class PluginMarketplaceService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def _get_or_create_listing(self, tenant_id: str, plugin_id: str) -> PluginMarketplaceListingModel:
        existing = await self.repos.plugin_marketplace_listings.get_for_plugin(tenant_id, plugin_id)
        if existing is not None:
            return existing
        listing = PluginMarketplaceListingModel(
            tenant_id=tenant_id, plugin_id=plugin_id,
            review_status=MarketplaceReviewStatus.PENDING.value, is_listed=False, install_count=0,
        )
        return await self.repos.plugin_marketplace_listings.add(listing)

    async def submit_for_review(self, tenant_id: str, plugin_id: str) -> PluginMarketplaceListingModel:
        listing = await self._get_or_create_listing(tenant_id, plugin_id)
        if not self.settings.plugin_marketplace_requires_review:
            return await self._approve_and_list(listing, reviewer_id="system-auto")
        listing.review_status = MarketplaceReviewStatus.PENDING.value
        return await self.repos.plugin_marketplace_listings.update(listing)

    async def approve(self, tenant_id: str, plugin_id: str, *, reviewer_id: str) -> PluginMarketplaceListingModel:
        listing = await self._get_or_create_listing(tenant_id, plugin_id)
        return await self._approve_and_list(listing, reviewer_id=reviewer_id)

    async def reject(self, tenant_id: str, plugin_id: str, *, reviewer_id: str) -> PluginMarketplaceListingModel:
        listing = await self._get_or_create_listing(tenant_id, plugin_id)
        listing.review_status = MarketplaceReviewStatus.REJECTED.value
        listing.reviewer_id = reviewer_id
        listing.reviewed_at = utcnow()
        listing.is_listed = False
        return await self.repos.plugin_marketplace_listings.update(listing)

    async def _approve_and_list(self, listing: PluginMarketplaceListingModel, *, reviewer_id: str) -> PluginMarketplaceListingModel:
        listing.review_status = MarketplaceReviewStatus.APPROVED.value
        listing.reviewer_id = reviewer_id
        listing.reviewed_at = utcnow()
        listing.is_listed = True
        return await self.repos.plugin_marketplace_listings.update(listing)

    async def record_install(self, tenant_id: str, plugin_id: str) -> PluginMarketplaceListingModel:
        listing = await self._get_or_create_listing(tenant_id, plugin_id)
        listing.install_count += 1
        return await self.repos.plugin_marketplace_listings.update(listing)

    async def set_rating(self, tenant_id: str, plugin_id: str, rating_avg: float) -> PluginMarketplaceListingModel:
        if not 0.0 <= rating_avg <= 5.0:
            raise ValidationError("rating_avg must be between 0.0 and 5.0")
        listing = await self._get_or_create_listing(tenant_id, plugin_id)
        listing.rating_avg = rating_avg
        return await self.repos.plugin_marketplace_listings.update(listing)

    async def list_public(self, tenant_id: str) -> list[PluginMarketplaceListingModel]:
        return await self.repos.plugin_marketplace_listings.list_listed(tenant_id)
