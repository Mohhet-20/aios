import uuid

import pytest

from developer_platform.config.settings import Settings
from developer_platform.core.exceptions import ValidationError
from developer_platform.plugin_sdk.lifecycle_service import PluginLifecycleService
from developer_platform.plugin_sdk.marketplace_service import PluginMarketplaceService

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_submit_requires_review_by_default(repos, db_session):
    tenant_id = _tid()
    lifecycle = PluginLifecycleService(repos)
    marketplace = PluginMarketplaceService(repos)
    plugin = await lifecycle.register_plugin(tenant_id, name="review-me", category="tool")
    await db_session.commit()

    listing = await marketplace.submit_for_review(tenant_id, plugin.id)
    await db_session.commit()
    assert listing.review_status == "pending"
    assert listing.is_listed is False


async def test_approve_lists_plugin(repos, db_session):
    tenant_id = _tid()
    lifecycle = PluginLifecycleService(repos)
    marketplace = PluginMarketplaceService(repos)
    plugin = await lifecycle.register_plugin(tenant_id, name="approve-me", category="tool")
    await db_session.commit()
    await marketplace.submit_for_review(tenant_id, plugin.id)
    await db_session.commit()

    approved = await marketplace.approve(tenant_id, plugin.id, reviewer_id="reviewer-1")
    await db_session.commit()
    assert approved.review_status == "approved"
    assert approved.is_listed is True
    assert approved.reviewer_id == "reviewer-1"

    public = await marketplace.list_public(tenant_id)
    assert any(listing.plugin_id == plugin.id for listing in public)


async def test_reject_keeps_unlisted(repos, db_session):
    tenant_id = _tid()
    lifecycle = PluginLifecycleService(repos)
    marketplace = PluginMarketplaceService(repos)
    plugin = await lifecycle.register_plugin(tenant_id, name="reject-me", category="tool")
    await db_session.commit()
    await marketplace.submit_for_review(tenant_id, plugin.id)
    await db_session.commit()

    rejected = await marketplace.reject(tenant_id, plugin.id, reviewer_id="reviewer-1")
    await db_session.commit()
    assert rejected.review_status == "rejected"
    assert rejected.is_listed is False


async def test_submit_auto_lists_when_review_not_required(repos, db_session):
    tenant_id = _tid()
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", secret_key="x" * 32, plugin_marketplace_requires_review=False)
    lifecycle = PluginLifecycleService(repos)
    marketplace = PluginMarketplaceService(repos, settings=settings)
    plugin = await lifecycle.register_plugin(tenant_id, name="auto-list", category="tool")
    await db_session.commit()

    listing = await marketplace.submit_for_review(tenant_id, plugin.id)
    await db_session.commit()
    assert listing.is_listed is True
    assert listing.review_status == "approved"


async def test_record_install_increments_count(repos, db_session):
    tenant_id = _tid()
    lifecycle = PluginLifecycleService(repos)
    marketplace = PluginMarketplaceService(repos)
    plugin = await lifecycle.register_plugin(tenant_id, name="install-me", category="tool")
    await db_session.commit()

    await marketplace.record_install(tenant_id, plugin.id)
    await marketplace.record_install(tenant_id, plugin.id)
    await db_session.commit()

    listing = await marketplace._get_or_create_listing(tenant_id, plugin.id)
    assert listing.install_count == 2


async def test_set_rating_validates_range(repos, db_session):
    tenant_id = _tid()
    lifecycle = PluginLifecycleService(repos)
    marketplace = PluginMarketplaceService(repos)
    plugin = await lifecycle.register_plugin(tenant_id, name="rate-me", category="tool")
    await db_session.commit()

    rated = await marketplace.set_rating(tenant_id, plugin.id, 4.5)
    await db_session.commit()
    assert rated.rating_avg == 4.5

    with pytest.raises(ValidationError):
        await marketplace.set_rating(tenant_id, plugin.id, 9.0)
