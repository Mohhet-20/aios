import uuid

import pytest

from developer_platform.config.settings import Settings
from developer_platform.core.exceptions import InvalidTransitionError, PluginAlreadyPublishedError, PluginSigningRequiredError
from developer_platform.plugin_sdk.lifecycle_service import PluginLifecycleService
from developer_platform.plugin_sdk.manifest import scaffold_manifest

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_register_plugin_is_idempotent(repos, db_session):
    tenant_id = _tid()
    service = PluginLifecycleService(repos)
    first = await service.register_plugin(tenant_id, name="my-plugin", category="tool")
    await db_session.commit()
    second = await service.register_plugin(tenant_id, name="my-plugin", category="tool")
    await db_session.commit()
    assert first.id == second.id


async def test_full_lifecycle_draft_to_published(repos, db_session):
    tenant_id = _tid()
    service = PluginLifecycleService(repos)
    plugin = await service.register_plugin(tenant_id, name="lifecycle-plugin", category="tool")
    await db_session.commit()

    manifest = scaffold_manifest(name="lifecycle-plugin", category="tool")
    version = await service.create_version(tenant_id, plugin.id, version="1.0.0", manifest=manifest)
    await db_session.commit()
    assert version.status == "draft"

    validated = await service.validate_version(tenant_id, version.id)
    await db_session.commit()
    assert validated.status == "validated"
    assert validated.validation_errors == []

    signed = await service.sign_version(tenant_id, version.id, signed_by="dev-1")
    await db_session.commit()
    assert signed.status == "signed"
    assert signed.signature is not None

    published = await service.publish_version(tenant_id, version.id)
    await db_session.commit()
    assert published.status == "published"

    assert await service.verify_signature(tenant_id, version.id) is True


async def test_validate_invalid_manifest_stays_in_draft(repos, db_session):
    tenant_id = _tid()
    service = PluginLifecycleService(repos)
    plugin = await service.register_plugin(tenant_id, name="bad-plugin", category="tool")
    await db_session.commit()

    version = await service.create_version(tenant_id, plugin.id, version="1.0.0", manifest={})
    await db_session.commit()

    validated = await service.validate_version(tenant_id, version.id)
    await db_session.commit()
    assert validated.status == "draft"
    assert len(validated.validation_errors) > 0


async def test_publish_without_signature_raises_when_required(repos, db_session):
    tenant_id = _tid()
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", secret_key="x" * 32, plugin_signing_required_for_publish=True)
    service = PluginLifecycleService(repos, settings=settings)
    plugin = await service.register_plugin(tenant_id, name="strict-plugin", category="tool")
    await db_session.commit()

    manifest = scaffold_manifest(name="strict-plugin", category="tool")
    version = await service.create_version(tenant_id, plugin.id, version="1.0.0", manifest=manifest)
    await service.validate_version(tenant_id, version.id)
    await db_session.commit()

    with pytest.raises(PluginSigningRequiredError):
        await service.publish_version(tenant_id, version.id)


async def test_publish_auto_signs_when_signing_not_required(repos, db_session):
    tenant_id = _tid()
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", secret_key="x" * 32, plugin_signing_required_for_publish=False)
    service = PluginLifecycleService(repos, settings=settings)
    plugin = await service.register_plugin(tenant_id, name="lenient-plugin", category="tool")
    await db_session.commit()

    manifest = scaffold_manifest(name="lenient-plugin", category="tool")
    version = await service.create_version(tenant_id, plugin.id, version="1.0.0", manifest=manifest)
    await service.validate_version(tenant_id, version.id)
    await db_session.commit()

    published = await service.publish_version(tenant_id, version.id)
    await db_session.commit()
    assert published.status == "published"
    assert published.signed_by == "system-auto"


async def test_publish_twice_raises_already_published(repos, db_session):
    tenant_id = _tid()
    service = PluginLifecycleService(repos)
    plugin = await service.register_plugin(tenant_id, name="double-publish", category="tool")
    await db_session.commit()
    manifest = scaffold_manifest(name="double-publish", category="tool")
    version = await service.create_version(tenant_id, plugin.id, version="1.0.0", manifest=manifest)
    await service.validate_version(tenant_id, version.id)
    await service.sign_version(tenant_id, version.id, signed_by="dev-1")
    await service.publish_version(tenant_id, version.id)
    await db_session.commit()

    with pytest.raises(PluginAlreadyPublishedError):
        await service.publish_version(tenant_id, version.id)


async def test_invalid_transition_raises(repos, db_session):
    tenant_id = _tid()
    service = PluginLifecycleService(repos)
    plugin = await service.register_plugin(tenant_id, name="skip-plugin", category="tool")
    await db_session.commit()
    manifest = scaffold_manifest(name="skip-plugin", category="tool")
    version = await service.create_version(tenant_id, plugin.id, version="1.0.0", manifest=manifest)
    await db_session.commit()

    with pytest.raises(InvalidTransitionError):
        await service.sign_version(tenant_id, version.id, signed_by="dev-1")


async def test_deprecate_version(repos, db_session):
    tenant_id = _tid()
    service = PluginLifecycleService(repos)
    plugin = await service.register_plugin(tenant_id, name="deprecate-plugin", category="tool")
    await db_session.commit()
    manifest = scaffold_manifest(name="deprecate-plugin", category="tool")
    version = await service.create_version(tenant_id, plugin.id, version="1.0.0", manifest=manifest)
    await service.validate_version(tenant_id, version.id)
    await service.sign_version(tenant_id, version.id, signed_by="dev-1")
    await service.publish_version(tenant_id, version.id)
    await db_session.commit()

    deprecated = await service.deprecate_version(tenant_id, version.id)
    await db_session.commit()
    assert deprecated.status == "deprecated"
