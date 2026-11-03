import pytest

from docs_platform.core.exceptions import VersionProtectedError
from docs_platform.documentation.doc_page_service import DocPageService
from docs_platform.documentation.doc_space_service import DocSpaceService
from docs_platform.security.governance_service import GovernanceService

pytestmark = pytest.mark.asyncio

TENANT = "t-security"


async def test_draft_page_is_editable(repos):
    space_svc = DocSpaceService(repos)
    page_svc = DocPageService(repos)
    space = await space_svc.register_space(TENANT, key="gov-space", name="Gov Space", doc_type="developer")
    page = await page_svc.create_page(TENANT, space.id, title="Draft Page", slug="draft-page", doc_type="developer")

    gov = GovernanceService()
    gov.assert_editable(page)  # should not raise


async def test_published_page_is_version_protected(repos):
    space_svc = DocSpaceService(repos)
    page_svc = DocPageService(repos)
    space = await space_svc.register_space(TENANT, key="gov-space-2", name="Gov Space 2", doc_type="developer")
    page = await page_svc.create_page(TENANT, space.id, title="Pub Page", slug="pub-page", doc_type="developer")
    await page_svc.submit_for_review(TENANT, page.id)
    page = await page_svc.publish(TENANT, page.id)

    gov = GovernanceService()
    with pytest.raises(VersionProtectedError):
        gov.assert_editable(page)
