import uuid

import pytest

from developer_platform.developer_analytics.dashboard_service import DeveloperActivityDashboardService
from developer_platform.developer_analytics.usage_service import UsageAnalyticsService

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_build_summary_counts_by_type(repos, db_session):
    tenant_id = _tid()
    usage = UsageAnalyticsService(repos)
    dashboard = DeveloperActivityDashboardService(repos)

    await usage.record_sdk_call(tenant_id)
    await usage.record_sdk_call(tenant_id)
    await usage.record_api_error(tenant_id)
    await db_session.commit()

    summary = await dashboard.build_summary(tenant_id)
    assert summary["sdk_call"] == 2
    assert summary["api_error"] == 1


async def test_top_resources_ranks_by_frequency(repos, db_session):
    tenant_id = _tid()
    usage = UsageAnalyticsService(repos)
    dashboard = DeveloperActivityDashboardService(repos)

    await usage.record_plugin_install(tenant_id, resource_id="plugin-a")
    await usage.record_plugin_install(tenant_id, resource_id="plugin-a")
    await usage.record_plugin_install(tenant_id, resource_id="plugin-b")
    await db_session.commit()

    top = await dashboard.top_resources(tenant_id, event_type="plugin_install")
    assert top[0] == ("plugin-a", 2)
    assert top[1] == ("plugin-b", 1)


async def test_most_active_developers(repos, db_session):
    tenant_id = _tid()
    usage = UsageAnalyticsService(repos)
    dashboard = DeveloperActivityDashboardService(repos)

    await usage.record_cli_command(tenant_id, developer_id="dev-1")
    await usage.record_cli_command(tenant_id, developer_id="dev-1")
    await usage.record_cli_command(tenant_id, developer_id="dev-2")
    await db_session.commit()

    top = await dashboard.most_active_developers(tenant_id, event_type="cli_command")
    assert top[0] == ("dev-1", 2)
