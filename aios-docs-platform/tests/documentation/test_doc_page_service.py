import pytest

from docs_platform.core.exceptions import InvalidTransitionError, UnsupportedDocTypeError, ValidationError
from docs_platform.documentation.doc_page_service import DocPageService
from docs_platform.documentation.doc_space_service import DocSpaceService

pytestmark = pytest.mark.asyncio


async def _make_space(repos, key="page-space"):
    return await DocSpaceService(repos).register_space("t1", key=key, name="Space", doc_type="developer")


async def test_create_page_seeds_version_one(repos):
    space = await _make_space(repos, "create-space")
    pages = DocPageService(repos)
    page = await pages.create_page("t1", space.id, title="Getting Started", slug="getting-started", doc_type="developer", content="hello")
    assert page.status == "draft"
    assert page.current_version == 1
    versions = await repos.doc_versions.list_for_page("t1", page.id)
    assert len(versions) == 1
    assert versions[0].content_snapshot == "hello"


async def test_create_page_rejects_unsupported_doc_type(repos):
    space = await _make_space(repos, "bad-type-space")
    pages = DocPageService(repos)
    with pytest.raises(UnsupportedDocTypeError):
        await pages.create_page("t1", space.id, title="X", slug="x", doc_type="not-a-type")


async def test_update_content_only_while_draft(repos):
    space = await _make_space(repos, "update-space")
    pages = DocPageService(repos)
    page = await pages.create_page("t1", space.id, title="Doc", slug="doc", doc_type="developer")
    updated = await pages.update_content("t1", page.id, content="v2 content")
    assert updated.current_version == 2

    await pages.submit_for_review("t1", page.id)
    await pages.publish("t1", page.id)
    with pytest.raises(ValidationError):
        await pages.update_content("t1", page.id, content="should fail")


async def test_full_editorial_lifecycle(repos):
    space = await _make_space(repos, "lifecycle-space")
    pages = DocPageService(repos)
    page = await pages.create_page("t1", space.id, title="Lifecycle", slug="lifecycle", doc_type="developer")

    reviewed = await pages.submit_for_review("t1", page.id)
    assert reviewed.status == "in_review"

    published = await pages.publish("t1", page.id)
    assert published.status == "published"
    assert published.last_reviewed_at is not None

    deprecated = await pages.deprecate("t1", page.id)
    assert deprecated.status == "deprecated"

    archived = await pages.archive("t1", page.id)
    assert archived.status == "archived"

    with pytest.raises(InvalidTransitionError):
        await pages.archive("t1", page.id)


async def test_reject_returns_to_draft(repos):
    space = await _make_space(repos, "reject-space")
    pages = DocPageService(repos)
    page = await pages.create_page("t1", space.id, title="Reject Me", slug="reject-me", doc_type="developer")
    await pages.submit_for_review("t1", page.id)
    rejected = await pages.reject("t1", page.id)
    assert rejected.status == "draft"
    # draft again means content edits are allowed once more
    updated = await pages.update_content("t1", page.id, content="fixed")
    assert updated.current_version == 2


async def test_list_pages_and_list_for_space(repos):
    space = await _make_space(repos, "list-space")
    pages = DocPageService(repos)
    await pages.create_page("t1", space.id, title="A", slug="a", doc_type="developer")
    await pages.create_page("t1", space.id, title="B", slug="b", doc_type="developer")

    for_space = await pages.list_for_space("t1", space.id)
    assert len(for_space) == 2

    for_tenant = await pages.list_pages("t1", doc_type="developer")
    assert len(for_tenant) >= 2
