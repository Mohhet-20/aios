import pytest

from docs_platform.core.exceptions import DocVersionNotFoundError
from docs_platform.documentation.doc_page_service import DocPageService
from docs_platform.documentation.doc_space_service import DocSpaceService
from docs_platform.versioning.version_service import DocVersionService

pytestmark = pytest.mark.asyncio

TENANT = "t-versioning"


async def test_list_versions_and_diff(repos):
    space = await DocSpaceService(repos).register_space(TENANT, key="ver-space", name="Space", doc_type="developer")
    pages = DocPageService(repos)
    page = await pages.create_page(TENANT, space.id, title="Doc", slug="doc", doc_type="developer", content="v1 content")
    await pages.update_content(TENANT, page.id, content="v2 content")

    versions = DocVersionService(repos)
    history = await versions.list_versions(TENANT, page.id)
    assert len(history) == 2
    assert history[0].version_number == 1
    assert history[1].version_number == 2

    diff = await versions.diff(TENANT, page.id, from_version=1, to_version=2)
    assert any("v1 content" in line for line in diff)
    assert any("v2 content" in line for line in diff)


async def test_get_version_not_found(repos):
    versions = DocVersionService(repos)
    with pytest.raises(DocVersionNotFoundError):
        await versions.get_version(TENANT, "no-such-page", 1)
