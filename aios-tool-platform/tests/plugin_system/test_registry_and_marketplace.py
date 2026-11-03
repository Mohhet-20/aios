import pytest

from tool_platform.core.exceptions import ValidationError


@pytest.mark.asyncio
async def test_publish_plugin_signs_manifest(registry_service):
    plugin = await registry_service.publish_plugin(
        name="Slack Connector", author="Acme Inc", category="slack", manifest={"capabilities": ["network_access"]},
    )
    assert plugin.is_signed is True
    assert plugin.checksum and plugin.signature
    assert plugin.slug == "slack-connector"


@pytest.mark.asyncio
async def test_publish_plugin_duplicate_slug_rejected(registry_service):
    await registry_service.publish_plugin(name="Slack Connector", author="Acme Inc", category="slack")
    with pytest.raises(ValidationError):
        await registry_service.publish_plugin(name="Slack Connector", author="Someone Else", category="slack")


@pytest.mark.asyncio
async def test_publish_new_version_rotates_signature(registry_service):
    plugin = await registry_service.publish_plugin(
        name="GitHub Connector", author="Acme Inc", category="github", manifest={"capabilities": []},
    )
    old_checksum = plugin.checksum
    updated = await registry_service.publish_new_version(plugin.id, version="2.0.0", manifest={"capabilities": ["network_access"]})
    assert updated.latest_version == "2.0.0"
    assert updated.checksum != old_checksum


@pytest.mark.asyncio
async def test_add_dependency_rejects_self_dependency(registry_service):
    plugin = await registry_service.publish_plugin(name="A", author="Acme", category="custom")
    with pytest.raises(ValidationError):
        await registry_service.add_dependency(plugin.id, depends_on_plugin_id=plugin.id)


@pytest.mark.asyncio
async def test_suspend_plugin(registry_service):
    plugin = await registry_service.publish_plugin(name="Bad Plugin", author="Acme", category="custom")
    suspended = await registry_service.suspend_plugin(plugin.id, reason="security issue")
    assert suspended.status == "suspended"
    assert suspended.manifest["suspension_reason"] == "security issue"


@pytest.mark.asyncio
async def test_marketplace_search_excludes_suspended(registry_service, marketplace_service):
    await registry_service.publish_plugin(name="Good Plugin", author="Acme", category="slack")
    bad = await registry_service.publish_plugin(name="Bad Plugin", author="Acme", category="slack")
    await registry_service.suspend_plugin(bad.id, reason="issue")

    results = await marketplace_service.search(category="slack")
    assert {p.name for p in results} == {"Good Plugin"}


@pytest.mark.asyncio
async def test_marketplace_search_by_query(registry_service, marketplace_service):
    await registry_service.publish_plugin(name="Jira Ticket Creator", author="Acme", category="jira")
    await registry_service.publish_plugin(name="Slack Notifier", author="Acme", category="slack")
    results = await marketplace_service.search(query="jira")
    assert len(results) == 1
    assert results[0].name == "Jira Ticket Creator"


@pytest.mark.asyncio
async def test_version_constraint_checking(registry_service):
    assert registry_service.check_version_dependency("2.3.0", "^2.0.0") is True
    assert registry_service.check_version_dependency("3.0.0", "^2.0.0") is False
    assert registry_service.check_version_dependency("1.5.0", ">=1.0.0") is True
    assert registry_service.check_version_dependency("1.5.0", "*") is True
