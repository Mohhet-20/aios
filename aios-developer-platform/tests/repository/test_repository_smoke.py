import uuid

import pytest

from developer_platform.domain.enums import (
    ApiKeyStatus,
    PackageType,
    PackageVersionStatus,
    PluginVersionStatus,
    SdkLanguage,
    UsageEventType,
    WebhookDeliveryStatus,
)
from developer_platform.models.analytics import UsageEventModel
from developer_platform.models.api_platform import ApiKeyModel
from developer_platform.models.plugins import PluginModel, PluginVersionModel
from developer_platform.models.registry import RegistryPackageModel, RegistryPackageVersionModel
from developer_platform.models.sdk import SdkCompatibilityEntryModel
from developer_platform.models.webhooks import WebhookDeliveryModel, WebhookSubscriptionModel

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_api_key_repository_crud(repos, db_session):
    tenant_id = _tid()
    key = ApiKeyModel(
        tenant_id=tenant_id,
        name="test key",
        key_hash=uuid.uuid4().hex,
        key_prefix="dpk_abcd",
        scopes=["read"],
        status=ApiKeyStatus.ACTIVE.value,
        rate_limit_per_minute=60,
    )
    created = await repos.api_keys.add(key)
    await db_session.commit()

    fetched = await repos.api_keys.get_by_key_hash(created.key_hash)
    assert fetched is not None
    assert fetched.tenant_id == tenant_id

    listed = await repos.api_keys.list_for_tenant(tenant_id)
    assert len(listed) == 1


async def test_sdk_compatibility_entry_repository(repos, db_session):
    tenant_id = _tid()
    entry = SdkCompatibilityEntryModel(
        tenant_id=tenant_id,
        language=SdkLanguage.PYTHON.value,
        sdk_major_version=2,
        min_api_version="v1",
        is_supported=True,
    )
    await repos.sdk_compatibility_entries.add(entry)
    await db_session.commit()

    got = await repos.sdk_compatibility_entries.get_entry(tenant_id, SdkLanguage.PYTHON.value, 2)
    assert got is not None
    assert got.min_api_version == "v1"

    listed = await repos.sdk_compatibility_entries.list_for_language(tenant_id, SdkLanguage.PYTHON.value)
    assert len(listed) == 1


async def test_plugin_and_version_repository(repos, db_session):
    tenant_id = _tid()
    plugin = PluginModel(tenant_id=tenant_id, name="my-plugin", category="tool", owner_id="dev-1")
    plugin = await repos.plugins.add(plugin)
    await db_session.commit()

    fetched_plugin = await repos.plugins.get_by_name(tenant_id, "my-plugin")
    assert fetched_plugin is not None

    version = PluginVersionModel(
        tenant_id=tenant_id,
        plugin_id=plugin.id,
        version="0.1.0",
        manifest={"entrypoint": "main.py"},
        status=PluginVersionStatus.DRAFT.value,
    )
    await repos.plugin_versions.add(version)
    await db_session.commit()

    versions = await repos.plugin_versions.list_for_plugin(tenant_id, plugin.id)
    assert len(versions) == 1
    by_status = await repos.plugin_versions.list_by_status(tenant_id, plugin.id, PluginVersionStatus.DRAFT.value)
    assert len(by_status) == 1


async def test_webhook_subscription_and_delivery_repository(repos, db_session):
    tenant_id = _tid()
    sub = WebhookSubscriptionModel(
        tenant_id=tenant_id,
        target_url="https://example.com/hook",
        secret_ref=str(uuid.uuid4()),
        event_types=["sdk_call"],
        is_active=True,
    )
    sub = await repos.webhook_subscriptions.add(sub)
    await db_session.commit()

    active = await repos.webhook_subscriptions.list_active(tenant_id)
    assert len(active) == 1

    delivery = WebhookDeliveryModel(
        tenant_id=tenant_id,
        subscription_id=sub.id,
        event_type="sdk_call",
        payload={"hello": "world"},
        status=WebhookDeliveryStatus.FAILED.value,
        attempt_count=1,
        next_attempt_at=None,
    )
    await repos.webhook_deliveries.add(delivery)
    await db_session.commit()

    by_status = await repos.webhook_deliveries.list_by_status(tenant_id, WebhookDeliveryStatus.FAILED.value)
    assert len(by_status) == 1


async def test_registry_package_repository(repos, db_session):
    tenant_id = _tid()
    package = RegistryPackageModel(
        tenant_id=tenant_id,
        name="agent-starter",
        package_type=PackageType.AGENT_TEMPLATE.value,
        owner_id="dev-1",
    )
    package = await repos.registry_packages.add(package)
    await db_session.commit()

    fetched = await repos.registry_packages.get_by_name_type(
        tenant_id, "agent-starter", PackageType.AGENT_TEMPLATE.value
    )
    assert fetched is not None

    version = RegistryPackageVersionModel(
        tenant_id=tenant_id,
        package_id=package.id,
        version="1.0.0",
        status=PackageVersionStatus.DRAFT.value,
        dependencies=[],
    )
    await repos.registry_package_versions.add(version)
    await db_session.commit()

    versions = await repos.registry_package_versions.list_for_package(tenant_id, package.id)
    assert len(versions) == 1


async def test_usage_event_repository(repos, db_session):
    tenant_id = _tid()
    for _ in range(3):
        event = UsageEventModel(
            tenant_id=tenant_id,
            event_type=UsageEventType.SDK_CALL.value,
            event_metadata={"language": "python"},
        )
        await repos.usage_events.add(event)
    await db_session.commit()

    recent = await repos.usage_events.list_recent(tenant_id, event_type=UsageEventType.SDK_CALL.value)
    assert len(recent) == 3

    counts = await repos.usage_events.count_by_type(tenant_id)
    assert counts.get(UsageEventType.SDK_CALL.value) == 3
