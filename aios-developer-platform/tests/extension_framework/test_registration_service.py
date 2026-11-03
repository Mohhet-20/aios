import uuid

import pytest

from developer_platform.core.exceptions import ExtensionRegistrationError
from developer_platform.extension_framework.point_service import ExtensionPointService
from developer_platform.extension_framework.registration_service import ExtensionRegistrationService

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_register_activate_disable_reactivate(repos, db_session):
    tenant_id = _tid()
    points = ExtensionPointService(repos)
    registrations = ExtensionRegistrationService(repos)

    point = await points.register_point(tenant_id, category="dashboard", name="widget-slot")
    await db_session.commit()

    registration = await registrations.register(tenant_id, extension_point_id=point.id, name="my-widget")
    await db_session.commit()
    assert registration.status == "registered"

    activated = await registrations.activate(registration.id)
    await db_session.commit()
    assert activated.status == "active"

    disabled = await registrations.disable(registration.id)
    await db_session.commit()
    assert disabled.status == "disabled"

    reactivated = await registrations.activate(registration.id)
    await db_session.commit()
    assert reactivated.status == "active"


async def test_registration_requires_contract_fields(repos, db_session):
    tenant_id = _tid()
    points = ExtensionPointService(repos)
    registrations = ExtensionRegistrationService(repos)

    point = await points.register_point(
        tenant_id, category="notification", name="slack-channel",
        contract_schema={"required": ["webhook_url"]},
    )
    await db_session.commit()

    with pytest.raises(ExtensionRegistrationError):
        await registrations.register(tenant_id, extension_point_id=point.id, name="my-notifier", config={})

    ok = await registrations.register(
        tenant_id, extension_point_id=point.id, name="my-notifier", config={"webhook_url": "https://x"},
    )
    await db_session.commit()
    assert ok.status == "registered"


async def test_double_disable_raises(repos, db_session):
    tenant_id = _tid()
    points = ExtensionPointService(repos)
    registrations = ExtensionRegistrationService(repos)

    point = await points.register_point(tenant_id, category="tool", name="custom-tool")
    await db_session.commit()
    registration = await registrations.register(tenant_id, extension_point_id=point.id, name="reg-1")
    await db_session.commit()

    await registrations.disable(registration.id)
    await db_session.commit()

    with pytest.raises(ExtensionRegistrationError):
        await registrations.disable(registration.id)


async def test_list_for_point_and_plugin(repos, db_session):
    tenant_id = _tid()
    points = ExtensionPointService(repos)
    registrations = ExtensionRegistrationService(repos)

    point = await points.register_point(tenant_id, category="agent", name="agent-hook")
    await db_session.commit()

    await registrations.register(tenant_id, extension_point_id=point.id, name="reg-a", plugin_id="plugin-1")
    await registrations.register(tenant_id, extension_point_id=point.id, name="reg-b", plugin_id="plugin-1")
    await db_session.commit()

    for_point = await registrations.list_for_point(tenant_id, point.id)
    assert len(for_point) == 2

    for_plugin = await registrations.list_for_plugin(tenant_id, "plugin-1")
    assert len(for_plugin) == 2
