"""Documentation Analytics: raw event recording plus the aggregations
the prompt calls for (page views, search queries, tutorial completion,
failed searches, most-viewed docs, feedback scores, broken links,
content freshness). Split into three small services rather than one
god-object, mirroring the granularity of the three underlying tables
(events / feedback / broken links) — each has a distinct write shape
and a distinct set of readers."""
from __future__ import annotations


from docs_platform.analytics.aggregation_rules import (
    average_feedback_score,
    content_freshness_score,
    failed_search_rate,
    most_viewed,
    tutorial_completion_rate,
)
from docs_platform.config.settings import Settings
from docs_platform.core.exceptions import NotFoundError, ValidationError
from docs_platform.models.analytics import AnalyticsEventModel, BrokenLinkModel, FeedbackModel
from docs_platform.repositories.registry import RepositoryRegistry
from docs_platform.clock import utc_now

_VALID_EVENT_TYPES = {
    "page_view", "search_query", "tutorial_started", "tutorial_completed", "feedback_submitted",
}


class AnalyticsEventService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record_event(self, tenant_id: str, *, event_type: str, subject_ref: str | None = None, metadata: dict | None = None) -> AnalyticsEventModel:
        if event_type not in _VALID_EVENT_TYPES:
            raise ValidationError(f"Unsupported event_type: {event_type!r}")
        event = AnalyticsEventModel(
            tenant_id=tenant_id, event_type=event_type, subject_ref=subject_ref, event_metadata=metadata or {},
        )
        return await self.repos.analytics_events.add(event)

    async def most_viewed_pages(self, tenant_id: str, *, limit: int = 10) -> list[tuple[str, int]]:
        events = await self.repos.analytics_events.list_for_tenant(tenant_id, event_type="page_view")
        return most_viewed(events, limit=limit)

    async def failed_search_rate(self, tenant_id: str) -> float:
        events = await self.repos.analytics_events.list_for_tenant(tenant_id, event_type="search_query")
        return failed_search_rate(events)

    async def tutorial_completion_rate(self, tenant_id: str) -> float:
        started = await self.repos.analytics_events.list_for_tenant(tenant_id, event_type="tutorial_started")
        completed = await self.repos.analytics_events.list_for_tenant(tenant_id, event_type="tutorial_completed")
        return tutorial_completion_rate(started + completed)


class FeedbackService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def submit_feedback(self, tenant_id: str, *, subject_ref: str, score: int, comment: str | None = None) -> FeedbackModel:
        if not (1 <= score <= 5):
            raise ValidationError("Feedback score must be between 1 and 5")
        feedback = FeedbackModel(tenant_id=tenant_id, subject_ref=subject_ref, score=score, comment=comment)
        return await self.repos.feedback.add(feedback)

    async def average_score(self, tenant_id: str, subject_ref: str) -> float | None:
        rows = await self.repos.feedback.list_for_subject(tenant_id, subject_ref)
        return average_feedback_score(rows)

    async def list_for_subject(self, tenant_id: str, subject_ref: str) -> list[FeedbackModel]:
        return await self.repos.feedback.list_for_subject(tenant_id, subject_ref)


class BrokenLinkService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def report(self, tenant_id: str, *, source_ref: str, url: str) -> BrokenLinkModel:
        link = BrokenLinkModel(tenant_id=tenant_id, source_ref=source_ref, url=url)
        return await self.repos.broken_links.add(link)

    async def get_or_404(self, tenant_id: str, link_id: str) -> BrokenLinkModel:
        link = await self.repos.broken_links.get(link_id)
        if link is None or link.tenant_id != tenant_id:
            raise NotFoundError(f"Broken link {link_id} not found")
        return link

    async def resolve(self, tenant_id: str, link_id: str) -> BrokenLinkModel:
        link = await self.get_or_404(tenant_id, link_id)
        link.resolved = True
        return link

    async def list_unresolved(self, tenant_id: str) -> list[BrokenLinkModel]:
        return await self.repos.broken_links.list_unresolved(tenant_id)


class ContentFreshnessService:
    """Scores published pages by how recently they were reviewed —
    reuses the same staleness-window setting the AI assistant's
    `detect_outdated_pages` uses, but returns a continuous score per
    page rather than a binary outdated/not list, since analytics wants
    a distribution and the assistant just wants a worklist."""

    def __init__(self, repos: RepositoryRegistry, settings: Settings):
        self.repos = repos
        self.settings = settings

    async def score_tenant_pages(self, tenant_id: str) -> list[tuple[str, float]]:
        pages = await self.repos.doc_pages.list_for_tenant(tenant_id, status="published")
        now = utc_now()
        window = self.settings.analytics_freshness_window_days
        return [
            (page.id, content_freshness_score(page.last_reviewed_at, now=now, window_days=window))
            for page in pages
        ]
