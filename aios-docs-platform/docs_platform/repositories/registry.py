"""Unit-of-work: lazily builds and memoizes one repository per model,
all sharing a single `AsyncSession` (and therefore the same
transaction) for the lifetime of a request or test."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from docs_platform.repositories.analytics_repository import AnalyticsEventRepository, BrokenLinkRepository, FeedbackRepository
from docs_platform.repositories.api_sdk_docs_repository import ApiDocEntryRepository, GenerationJobRepository, SdkDocEntryRepository
from docs_platform.repositories.architecture_repository import DiagramRepository, TechStackEntryRepository
from docs_platform.repositories.assistant_repository import AssistantSessionRepository
from docs_platform.repositories.collaboration_repository import AuditLogEntryRepository, CommentRepository, ReviewRepository
from docs_platform.repositories.documentation_repository import DocPageRepository, DocSpaceRepository
from docs_platform.repositories.knowledge_base_repository import KbArticleRepository
from docs_platform.repositories.learning_repository import EnrollmentRepository, LearningPathRepository, TutorialRepository
from docs_platform.repositories.search_repository import SearchQueryLogRepository
from docs_platform.repositories.security_repository import RoleAssignmentRepository
from docs_platform.repositories.versioning_repository import (
    DeprecationNoticeRepository,
    DocVersionRepository,
    ReleaseNoteRepository,
)


class RepositoryRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session
        self._repos: dict[str, object] = {}

    def _get(self, key: str, cls: type) -> object:
        if key not in self._repos:
            self._repos[key] = cls(self.session)
        return self._repos[key]

    # -- documentation core --
    @property
    def doc_spaces(self) -> DocSpaceRepository:
        return self._get("doc_spaces", DocSpaceRepository)

    @property
    def doc_pages(self) -> DocPageRepository:
        return self._get("doc_pages", DocPageRepository)

    # -- API & SDK documentation / automation --
    @property
    def api_doc_entries(self) -> ApiDocEntryRepository:
        return self._get("api_doc_entries", ApiDocEntryRepository)

    @property
    def sdk_doc_entries(self) -> SdkDocEntryRepository:
        return self._get("sdk_doc_entries", SdkDocEntryRepository)

    @property
    def generation_jobs(self) -> GenerationJobRepository:
        return self._get("generation_jobs", GenerationJobRepository)

    # -- architecture portal --
    @property
    def diagrams(self) -> DiagramRepository:
        return self._get("diagrams", DiagramRepository)

    @property
    def tech_stack_entries(self) -> TechStackEntryRepository:
        return self._get("tech_stack_entries", TechStackEntryRepository)

    # -- knowledge base --
    @property
    def kb_articles(self) -> KbArticleRepository:
        return self._get("kb_articles", KbArticleRepository)

    # -- learning platform --
    @property
    def tutorials(self) -> TutorialRepository:
        return self._get("tutorials", TutorialRepository)

    @property
    def learning_paths(self) -> LearningPathRepository:
        return self._get("learning_paths", LearningPathRepository)

    @property
    def enrollments(self) -> EnrollmentRepository:
        return self._get("enrollments", EnrollmentRepository)

    # -- AI documentation assistant --
    @property
    def assistant_sessions(self) -> AssistantSessionRepository:
        return self._get("assistant_sessions", AssistantSessionRepository)

    # -- search platform --
    @property
    def search_query_logs(self) -> SearchQueryLogRepository:
        return self._get("search_query_logs", SearchQueryLogRepository)

    # -- versioning & release notes --
    @property
    def doc_versions(self) -> DocVersionRepository:
        return self._get("doc_versions", DocVersionRepository)

    @property
    def release_notes(self) -> ReleaseNoteRepository:
        return self._get("release_notes", ReleaseNoteRepository)

    @property
    def deprecation_notices(self) -> DeprecationNoticeRepository:
        return self._get("deprecation_notices", DeprecationNoticeRepository)

    # -- collaboration --
    @property
    def comments(self) -> CommentRepository:
        return self._get("comments", CommentRepository)

    @property
    def reviews(self) -> ReviewRepository:
        return self._get("reviews", ReviewRepository)

    @property
    def audit_log_entries(self) -> AuditLogEntryRepository:
        return self._get("audit_log_entries", AuditLogEntryRepository)

    # -- analytics --
    @property
    def analytics_events(self) -> AnalyticsEventRepository:
        return self._get("analytics_events", AnalyticsEventRepository)

    @property
    def feedback(self) -> FeedbackRepository:
        return self._get("feedback", FeedbackRepository)

    @property
    def broken_links(self) -> BrokenLinkRepository:
        return self._get("broken_links", BrokenLinkRepository)

    # -- security & governance --
    @property
    def role_assignments(self) -> RoleAssignmentRepository:
        return self._get("role_assignments", RoleAssignmentRepository)
