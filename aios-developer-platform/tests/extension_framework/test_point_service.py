import uuid

import pytest

from developer_platform.core.exceptions import ExtensionPointNotFoundError, ValidationError
from developer_platform.extension_framework.point_service import ExtensionPointService

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_register_point_is_idempotent(repos, db_session):
    tenant_id = _tid()
    service = ExtensionPointService(repos)
    first = await service.register_point(tenant_id, category="tool", name="custom-tool-hook")
    await db_session.commit()
    second = await service.register_point(tenant_id, category="tool", name="custom-tool-hook")
    await db_session.commit()
    assert first.id == second.id


async def test_register_invalid_category_raises(repos, db_session):
    service = ExtensionPointService(repos)
    with pytest.raises(ValidationError):
        await service.register_point(_tid(), category="not-a-category", name="x")


async def test_get_point_not_found_raises(repos, db_session):
    service = ExtensionPointService(repos)
    with pytest.raises(ExtensionPointNotFoundError):
        await service.get_point(_tid(), category="tool", name="missing")


async def test_list_all_covers_every_category(repos, db_session):
    tenant_id = _tid()
    service = ExtensionPointService(repos)
    categories = [
        "agent", "prompt", "workflow", "memory", "tool", "model",
        "evaluation", "dashboard", "authentication", "notification", "ui_component",
    ]
    for category in categories:
        await service.register_point(tenant_id, category=category, name=f"{category}-hook")
    await db_session.commit()

    all_points = await service.list_all(tenant_id)
    assert {p.category for p in all_points} == set(categories)
    assert len(all_points) == 11
