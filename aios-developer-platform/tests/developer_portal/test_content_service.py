import uuid

import pytest

from developer_platform.core.exceptions import PortalError, ValidationError
from developer_platform.developer_portal.content_service import PortalContentService

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_create_and_publish_content(repos, db_session):
    tenant_id = _tid()
    service = PortalContentService(repos)
    content = await service.create_content(tenant_id, content_type="doc", slug="getting-started", title="Getting Started")
    await db_session.commit()
    assert content.status == "draft"
    assert content.version == 1

    published = await service.publish(content.id)
    await db_session.commit()
    assert published.status == "published"

    fetched = await service.get_by_slug(tenant_id, "doc", "getting-started")
    assert fetched.id == content.id


async def test_duplicate_slug_raises(repos, db_session):
    tenant_id = _tid()
    service = PortalContentService(repos)
    await service.create_content(tenant_id, content_type="doc", slug="dup", title="One")
    await db_session.commit()
    with pytest.raises(ValidationError):
        await service.create_content(tenant_id, content_type="doc", slug="dup", title="Two")


async def test_invalid_content_type_raises(repos, db_session):
    service = PortalContentService(repos)
    with pytest.raises(ValidationError):
        await service.create_content(_tid(), content_type="not-a-type", slug="x", title="X")


async def test_update_body_increments_version(repos, db_session):
    tenant_id = _tid()
    service = PortalContentService(repos)
    content = await service.create_content(tenant_id, content_type="tutorial", slug="tut-1", title="Tut", body="v1")
    await db_session.commit()

    updated = await service.update_content(content.id, body="v2")
    await db_session.commit()
    assert updated.version == 2
    assert updated.body == "v2"

    # Title-only update does not bump version.
    updated_again = await service.update_content(content.id, title="New Title")
    await db_session.commit()
    assert updated_again.version == 2


async def test_archive_then_republish(repos, db_session):
    tenant_id = _tid()
    service = PortalContentService(repos)
    content = await service.create_content(tenant_id, content_type="quickstart", slug="qs-1", title="QS")
    await db_session.commit()
    await service.publish(content.id)
    await db_session.commit()

    archived = await service.archive(content.id)
    await db_session.commit()
    assert archived.status == "archived"

    republished = await service.publish(content.id)
    await db_session.commit()
    assert republished.status == "published"


async def test_invalid_transition_raises(repos, db_session):
    tenant_id = _tid()
    service = PortalContentService(repos)
    content = await service.create_content(tenant_id, content_type="release_notes", slug="rn-1", title="RN")
    await db_session.commit()
    with pytest.raises(PortalError):
        await service.archive(content.id)  # draft -> archived is not allowed


async def test_list_published_and_by_type(repos, db_session):
    tenant_id = _tid()
    service = PortalContentService(repos)
    a = await service.create_content(tenant_id, content_type="doc", slug="a", title="A")
    b = await service.create_content(tenant_id, content_type="doc", slug="b", title="B")
    await db_session.commit()
    await service.publish(a.id)
    await db_session.commit()

    published = await service.list_published(tenant_id)
    assert {c.id for c in published} == {a.id}

    by_type = await service.list_by_type(tenant_id, "doc")
    assert {c.id for c in by_type} == {a.id, b.id}
