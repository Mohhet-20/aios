import uuid

import pytest

from developer_platform.config.settings import Settings
from developer_platform.core.exceptions import AnalyticsError
from developer_platform.developer_analytics.usage_service import UsageAnalyticsService

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_record_event_rejects_unknown_type(repos, db_session):
    service = UsageAnalyticsService(repos)
    with pytest.raises(AnalyticsError):
        await service.record_event(_tid(), "not_a_real_event")


async def test_all_eight_event_type_helpers_record(repos, db_session):
    tenant_id = _tid()
    service = UsageAnalyticsService(repos)

    await service.record_sdk_call(tenant_id, developer_id="dev-1")
    await service.record_api_call(tenant_id, developer_id="dev-1")
    await service.record_cli_command(tenant_id, developer_id="dev-1")
    await service.record_plugin_install(tenant_id, developer_id="dev-1")
    await service.record_webhook_delivery(tenant_id, developer_id="dev-1")
    await service.record_developer_activity(tenant_id, developer_id="dev-1")
    await service.record_package_download(tenant_id, developer_id="dev-1")
    await service.record_api_error(tenant_id, developer_id="dev-1")
    await db_session.commit()

    summary = await service.get_summary(tenant_id)
    assert set(summary.keys()) == {
        "sdk_call", "api_call", "cli_command", "plugin_install",
        "webhook_delivery", "developer_activity", "package_download", "api_error",
    }
    assert all(count == 1 for count in summary.values())


async def test_sampling_below_rate_skips_persistence(repos, db_session):
    tenant_id = _tid()
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", secret_key="x" * 32, developer_analytics_sample_rate=0.5)
    service = UsageAnalyticsService(repos, settings=settings, rand=lambda: 0.9)  # 0.9 >= 0.5 -> sampled out

    result = await service.record_sdk_call(tenant_id)
    assert result is None

    recent = await service.list_recent(tenant_id)
    assert recent == []


async def test_sampling_within_rate_persists(repos, db_session):
    tenant_id = _tid()
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", secret_key="x" * 32, developer_analytics_sample_rate=0.5)
    service = UsageAnalyticsService(repos, settings=settings, rand=lambda: 0.1)  # 0.1 < 0.5 -> sampled in

    result = await service.record_sdk_call(tenant_id)
    await db_session.commit()
    assert result is not None


async def test_list_recent_filters_by_event_type(repos, db_session):
    tenant_id = _tid()
    service = UsageAnalyticsService(repos)
    await service.record_sdk_call(tenant_id)
    await service.record_api_error(tenant_id)
    await db_session.commit()

    sdk_only = await service.list_recent(tenant_id, event_type="sdk_call")
    assert len(sdk_only) == 1
    assert sdk_only[0].event_type == "sdk_call"


async def test_purge_old_events(repos, db_session):
    tenant_id = _tid()
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", secret_key="x" * 32, analytics_retention_days=-1)
    service = UsageAnalyticsService(repos, settings=settings)
    await service.record_sdk_call(tenant_id)
    await db_session.commit()

    deleted = await service.purge_old_events(tenant_id)
    await db_session.commit()
    assert deleted == 1

    remaining = await service.list_recent(tenant_id)
    assert remaining == []
