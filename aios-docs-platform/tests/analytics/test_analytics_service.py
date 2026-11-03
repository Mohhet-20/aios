import pytest

from docs_platform.analytics.analytics_service import (
    AnalyticsEventService,
    BrokenLinkService,
    ContentFreshnessService,
    FeedbackService,
)
from docs_platform.config.settings import Settings
from docs_platform.core.exceptions import NotFoundError, ValidationError
from docs_platform.documentation.doc_page_service import DocPageService
from docs_platform.documentation.doc_space_service import DocSpaceService

pytestmark = pytest.mark.asyncio

TENANT = "t-analytics"


async def test_record_event_rejects_unknown_type(repos):
    svc = AnalyticsEventService(repos)
    with pytest.raises(ValidationError):
        await svc.record_event(TENANT, event_type="bogus")


async def test_most_viewed_pages(repos):
    svc = AnalyticsEventService(repos)
    await svc.record_event(TENANT, event_type="page_view", subject_ref="page:a")
    await svc.record_event(TENANT, event_type="page_view", subject_ref="page:a")
    await svc.record_event(TENANT, event_type="page_view", subject_ref="page:b")
    result = await svc.most_viewed_pages(TENANT)
    assert result[0] == ("page:a", 2)


async def test_failed_search_rate(repos):
    svc = AnalyticsEventService(repos)
    await svc.record_event(TENANT, event_type="search_query", metadata={"result_count": 0})
    await svc.record_event(TENANT, event_type="search_query", metadata={"result_count": 2})
    rate = await svc.failed_search_rate(TENANT)
    assert rate == 0.5


async def test_tutorial_completion_rate(repos):
    svc = AnalyticsEventService(repos)
    await svc.record_event(TENANT, event_type="tutorial_started")
    await svc.record_event(TENANT, event_type="tutorial_started")
    await svc.record_event(TENANT, event_type="tutorial_completed")
    rate = await svc.tutorial_completion_rate(TENANT)
    assert rate == 0.5


async def test_feedback_rejects_out_of_range_score(repos):
    svc = FeedbackService(repos)
    with pytest.raises(ValidationError):
        await svc.submit_feedback(TENANT, subject_ref="page:x", score=6)


async def test_feedback_average_score(repos):
    svc = FeedbackService(repos)
    await svc.submit_feedback(TENANT, subject_ref="page:y", score=5)
    await svc.submit_feedback(TENANT, subject_ref="page:y", score=3)
    avg = await svc.average_score(TENANT, "page:y")
    assert avg == 4.0


async def test_broken_link_report_and_resolve(repos):
    svc = BrokenLinkService(repos)
    link = await svc.report(TENANT, source_ref="page:z", url="https://example.com/dead")
    assert link.resolved is False
    unresolved = await svc.list_unresolved(TENANT)
    assert any(entry.id == link.id for entry in unresolved)
    resolved = await svc.resolve(TENANT, link.id)
    assert resolved.resolved is True
    unresolved_after = await svc.list_unresolved(TENANT)
    assert all(entry.id != link.id for entry in unresolved_after)


async def test_broken_link_not_found_raises(repos):
    svc = BrokenLinkService(repos)
    with pytest.raises(NotFoundError):
        await svc.get_or_404(TENANT, "nonexistent-id")


async def test_content_freshness_scores_published_pages(repos):
    space_svc = DocSpaceService(repos)
    page_svc = DocPageService(repos)
    space = await space_svc.register_space(TENANT, key="freshness-space", name="Freshness Space", doc_type="developer")
    page = await page_svc.create_page(TENANT, space_id=space.id, title="Fresh Page", slug="fresh-page", doc_type="developer", content="hello")
    await page_svc.submit_for_review(TENANT, page.id)
    await page_svc.publish(TENANT, page.id)

    freshness_svc = ContentFreshnessService(repos, Settings())
    scores = await freshness_svc.score_tenant_pages(TENANT)
    assert any(pid == page.id for pid, _ in scores)
