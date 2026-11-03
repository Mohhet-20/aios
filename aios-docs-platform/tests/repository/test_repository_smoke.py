"""Schema smoke test: every repository can round-trip a minimal row for
its model, and RepositoryRegistry memoizes one instance per repository."""
from __future__ import annotations

import datetime as dt

import pytest

from docs_platform.models.analytics import AnalyticsEventModel, BrokenLinkModel, FeedbackModel
from docs_platform.models.api_sdk_docs import ApiDocEntryModel, GenerationJobModel, SdkDocEntryModel
from docs_platform.models.architecture import DiagramModel, TechStackEntryModel
from docs_platform.models.assistant import AssistantSessionModel
from docs_platform.models.collaboration import AuditLogEntryModel, CommentModel, ReviewModel
from docs_platform.models.documentation import DocPageModel, DocSpaceModel
from docs_platform.models.knowledge_base import KbArticleModel
from docs_platform.models.learning import EnrollmentModel, LearningPathModel, TutorialModel
from docs_platform.models.search import SearchQueryLogModel
from docs_platform.models.security import RoleAssignmentModel
from docs_platform.models.versioning import DeprecationNoticeModel, DocVersionModel, ReleaseNoteModel

pytestmark = pytest.mark.asyncio


async def test_registry_memoizes_repositories(repos):
    assert repos.doc_spaces is repos.doc_spaces
    assert repos.tutorials is repos.tutorials
    assert repos.doc_spaces is not repos.doc_pages


async def test_documentation_core_round_trip(repos):
    space = await repos.doc_spaces.add(DocSpaceModel(tenant_id="t1", key="core-arch", name="Architecture", doc_type="architecture"))
    await repos.session.commit()
    page = await repos.doc_pages.add(
        DocPageModel(tenant_id="t1", space_id=space.id, title="Overview", slug="overview", doc_type="architecture", status="draft")
    )
    await repos.session.commit()
    fetched = await repos.doc_pages.get(page.id)
    assert fetched is not None
    listed = await repos.doc_pages.list_for_space("t1", space.id)
    assert len(listed) == 1


async def test_api_sdk_docs_round_trip(repos):
    api_entry = await repos.api_doc_entries.add(
        ApiDocEntryModel(tenant_id="t1", protocol_type="rest", path="/v1/things", method="GET")
    )
    sdk_entry = await repos.sdk_doc_entries.add(
        SdkDocEntryModel(tenant_id="t1", sdk_language="python", package_ref="aios-sdk", title="Quickstart")
    )
    job = await repos.generation_jobs.add(
        GenerationJobModel(tenant_id="t1", job_type="api_docs", target_ref="svc:1", status="queued")
    )
    await repos.session.commit()
    assert (await repos.api_doc_entries.get(api_entry.id)) is not None
    assert (await repos.sdk_doc_entries.get(sdk_entry.id)) is not None
    assert (await repos.generation_jobs.get(job.id)) is not None


async def test_architecture_portal_round_trip(repos):
    diagram = await repos.diagrams.add(DiagramModel(tenant_id="t1", diagram_type="system_overview", title="System"))
    tech = await repos.tech_stack_entries.add(TechStackEntryModel(tenant_id="t1", category="backend", name="FastAPI"))
    await repos.session.commit()
    assert (await repos.diagrams.get(diagram.id)) is not None
    assert (await repos.tech_stack_entries.get(tech.id)) is not None


async def test_knowledge_base_round_trip(repos):
    await repos.kb_articles.add(
        KbArticleModel(tenant_id="t1", article_type="faq", title="Why?", slug="why", status="draft")
    )
    await repos.session.commit()
    assert (await repos.kb_articles.get_by_slug("t1", "why")) is not None


async def test_learning_platform_round_trip(repos):
    tutorial = await repos.tutorials.add(
        TutorialModel(tenant_id="t1", tutorial_type="getting_started", title="Hello AIOS", role="developer")
    )
    path = await repos.learning_paths.add(LearningPathModel(tenant_id="t1", name="Dev Track", role="developer"))
    enrollment = await repos.enrollments.add(
        EnrollmentModel(tenant_id="t1", user_id="u1", tutorial_id=tutorial.id, status="enrolled")
    )
    await repos.session.commit()
    assert (await repos.tutorials.get(tutorial.id)) is not None
    assert (await repos.learning_paths.get(path.id)) is not None
    assert (await repos.enrollments.get(enrollment.id)) is not None


async def test_assistant_and_search_round_trip(repos):
    session_row = await repos.assistant_sessions.add(
        AssistantSessionModel(tenant_id="t1", question="How do I deploy?")
    )
    query_log = await repos.search_query_logs.add(SearchQueryLogModel(tenant_id="t1", query="deploy", result_count=3))
    await repos.session.commit()
    assert (await repos.assistant_sessions.get(session_row.id)) is not None
    assert (await repos.search_query_logs.get(query_log.id)) is not None


async def test_versioning_round_trip(repos):
    now = dt.datetime.now(dt.timezone.utc)
    version = await repos.doc_versions.add(
        DocVersionModel(tenant_id="t1", page_id="p1", version_number=1, created_at=now)
    )
    note = await repos.release_notes.add(ReleaseNoteModel(tenant_id="t1", version_label="v1.0", title="Launch"))
    notice = await repos.deprecation_notices.add(
        DeprecationNoticeModel(tenant_id="t1", subject_ref="api:/v0/old", message="use /v1")
    )
    await repos.session.commit()
    assert (await repos.doc_versions.get(version.id)) is not None
    assert (await repos.release_notes.get(note.id)) is not None
    assert (await repos.deprecation_notices.get(notice.id)) is not None


async def test_collaboration_round_trip(repos):
    comment = await repos.comments.add(CommentModel(tenant_id="t1", target_ref="page:1", author_id="u1", body="typo here"))
    review = await repos.reviews.add(ReviewModel(tenant_id="t1", page_id="p1", requested_by="u1"))
    audit = await repos.audit_log_entries.add(
        AuditLogEntryModel(tenant_id="t1", action="page.published", target_ref="page:1")
    )
    await repos.session.commit()
    assert (await repos.comments.get(comment.id)) is not None
    assert (await repos.reviews.get(review.id)) is not None
    assert (await repos.audit_log_entries.get(audit.id)) is not None


async def test_analytics_and_security_round_trip(repos):
    event = await repos.analytics_events.add(AnalyticsEventModel(tenant_id="t1", event_type="page_view", subject_ref="page:1"))
    feedback = await repos.feedback.add(FeedbackModel(tenant_id="t1", subject_ref="page:1", score=5))
    link = await repos.broken_links.add(BrokenLinkModel(tenant_id="t1", source_ref="page:1", url="https://dead.example"))
    role = await repos.role_assignments.add(RoleAssignmentModel(tenant_id="t1", user_id="u1", role="editor"))
    await repos.session.commit()
    assert (await repos.analytics_events.get(event.id)) is not None
    assert (await repos.feedback.get(feedback.id)) is not None
    assert (await repos.broken_links.get(link.id)) is not None
    assert (await repos.role_assignments.get(role.id)) is not None
