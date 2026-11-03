import pytest

from docs_platform.core.exceptions import InvalidSearchQueryError
from docs_platform.documentation.doc_page_service import DocPageService
from docs_platform.documentation.doc_space_service import DocSpaceService
from docs_platform.search.search_service import SearchService

pytestmark = pytest.mark.asyncio

TENANT = "t-search"


async def _make_published_page(repos, *, slug, title, content, doc_type="developer"):
    space = await DocSpaceService(repos).register_space(TENANT, key=f"space-{slug}", name="Space", doc_type=doc_type)
    pages = DocPageService(repos)
    page = await pages.create_page(TENANT, space.id, title=title, slug=slug, doc_type=doc_type, content=content)
    await pages.submit_for_review(TENANT, page.id)
    return await pages.publish(TENANT, page.id)


async def test_search_rejects_too_short_query(repos):
    svc = SearchService(repos)
    with pytest.raises(InvalidSearchQueryError):
        await svc.search(TENANT, "a")


async def test_search_logs_query_and_returns_ranked_results(repos):
    await _make_published_page(repos, slug="search-target", title="Workflow Deployment", content="how to deploy a workflow")
    svc = SearchService(repos)
    results = await svc.search(TENANT, "deploy workflow")
    assert len(results) >= 1

    recent = await svc.recent_queries(TENANT)
    assert any(log.query == "deploy workflow" for log in recent)


async def test_search_with_no_matches_is_a_failed_search(repos):
    svc = SearchService(repos)
    results = await svc.search(TENANT, "zzzznomatch")
    assert results == []
    failed = await svc.failed_searches(TENANT)
    assert any(log.query == "zzzznomatch" for log in failed)


async def test_record_click_updates_log(repos):
    await _make_published_page(repos, slug="click-target", title="Clickable", content="click me content")
    svc = SearchService(repos)
    await svc.search(TENANT, "click me")
    logs = await svc.recent_queries(TENANT)
    log = logs[0]
    updated = await svc.record_click(TENANT, log.id, "page:some-id")
    assert updated.clicked_doc_ref == "page:some-id"


async def test_popular_queries_aggregates(repos):
    svc = SearchService(repos)
    await svc.search(TENANT, "workflow guide")
    await svc.search(TENANT, "workflow guide")
    await svc.search(TENANT, "agent guide")
    popular = await svc.popular_queries(TENANT)
    assert popular[0] == ("workflow guide", 2)
