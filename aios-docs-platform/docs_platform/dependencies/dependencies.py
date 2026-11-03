"""FastAPI dependency wiring: DB session -> RepositoryRegistry ->
every service. Auth is intentionally minimal here, matching every
sibling AIOS platform: this platform expects to sit behind an
already-authenticated gateway (in practice, the Identity Platform)
that forwards the caller's tenant via `X-Tenant-Id` and, where
relevant, the acting principal via `X-User-Id`. Every service is
built fresh per request off a per-request `RepositoryRegistry`/
`AsyncSession`, since a session must never be shared across
concurrent requests."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from docs_platform.analytics.analytics_service import (
    AnalyticsEventService,
    BrokenLinkService,
    ContentFreshnessService,
    FeedbackService,
)
from docs_platform.api_docs.api_doc_service import ApiDocService
from docs_platform.architecture.diagram_service import DiagramService
from docs_platform.architecture.tech_stack_service import TechStackService
from docs_platform.assistant.assistant_service import AssistantService
from docs_platform.automation.generation_job_service import GenerationJobService
from docs_platform.collaboration.audit_service import AuditLogService
from docs_platform.collaboration.comment_service import CommentService
from docs_platform.collaboration.review_service import ReviewService
from docs_platform.config.settings import Settings, get_settings
from docs_platform.database.session import session_scope
from docs_platform.documentation.doc_page_service import DocPageService
from docs_platform.documentation.doc_space_service import DocSpaceService
from docs_platform.knowledge.kb_article_service import KbArticleService
from docs_platform.learning.enrollment_service import EnrollmentService
from docs_platform.learning.learning_path_service import LearningPathService
from docs_platform.learning.tutorial_service import TutorialService
from docs_platform.repositories.registry import RepositoryRegistry
from docs_platform.sdk_docs.sdk_doc_service import SdkDocService
from docs_platform.search.search_service import SearchService
from docs_platform.security.governance_service import GovernanceService
from docs_platform.security.role_assignment_service import RoleAssignmentService
from docs_platform.security.visibility_service import VisibilityService
from docs_platform.versioning.deprecation_service import DeprecationService
from docs_platform.versioning.release_note_service import ReleaseNoteService
from docs_platform.versioning.version_service import DocVersionService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Delegates to `session_scope`, which commits on a clean exit and
    rolls back on any exception — a request handled through the REST
    API needs its writes to actually persist once the response is
    returned."""
    async for session in session_scope():
        yield session


async def get_repos(session: AsyncSession = Depends(get_session)) -> RepositoryRegistry:
    return RepositoryRegistry(session)


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_tenant_id(x_tenant_id: str | None = Header(default=None)) -> str:
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="Missing X-Tenant-Id header")
    return x_tenant_id


async def get_current_actor_id(x_user_id: str | None = Header(default=None)) -> str | None:
    """Unlike the tenant header, the actor header is optional — some of
    what this platform tracks (scheduled generation jobs, automated
    freshness scans) legitimately comes from a process with no human
    actor behind it."""
    return x_user_id


# -- documentation core ----------------------------------------------------------------------------------
async def get_doc_space_service(repos: RepositoryRegistry = Depends(get_repos)) -> DocSpaceService:
    return DocSpaceService(repos)


async def get_doc_page_service(repos: RepositoryRegistry = Depends(get_repos)) -> DocPageService:
    return DocPageService(repos)


# -- API / SDK documentation & automation -----------------------------------------------------------------
async def get_api_doc_service(repos: RepositoryRegistry = Depends(get_repos)) -> ApiDocService:
    return ApiDocService(repos)


async def get_sdk_doc_service(repos: RepositoryRegistry = Depends(get_repos)) -> SdkDocService:
    return SdkDocService(repos)


async def get_generation_job_service(repos: RepositoryRegistry = Depends(get_repos)) -> GenerationJobService:
    return GenerationJobService(repos)


# -- architecture portal ------------------------------------------------------------------------------------
async def get_diagram_service(repos: RepositoryRegistry = Depends(get_repos)) -> DiagramService:
    return DiagramService(repos)


async def get_tech_stack_service(repos: RepositoryRegistry = Depends(get_repos)) -> TechStackService:
    return TechStackService(repos)


# -- knowledge base -----------------------------------------------------------------------------------------
async def get_kb_article_service(repos: RepositoryRegistry = Depends(get_repos)) -> KbArticleService:
    return KbArticleService(repos)


# -- learning platform --------------------------------------------------------------------------------------
async def get_tutorial_service(repos: RepositoryRegistry = Depends(get_repos)) -> TutorialService:
    return TutorialService(repos)


async def get_learning_path_service(repos: RepositoryRegistry = Depends(get_repos)) -> LearningPathService:
    return LearningPathService(repos)


async def get_enrollment_service(repos: RepositoryRegistry = Depends(get_repos)) -> EnrollmentService:
    return EnrollmentService(repos)


# -- AI documentation assistant -----------------------------------------------------------------------------
async def get_assistant_service(repos: RepositoryRegistry = Depends(get_repos)) -> AssistantService:
    return AssistantService(repos)


# -- search platform -----------------------------------------------------------------------------------------
async def get_search_service(repos: RepositoryRegistry = Depends(get_repos)) -> SearchService:
    return SearchService(repos)


# -- versioning & release notes ---------------------------------------------------------------------------------
async def get_doc_version_service(repos: RepositoryRegistry = Depends(get_repos)) -> DocVersionService:
    return DocVersionService(repos)


async def get_release_note_service(repos: RepositoryRegistry = Depends(get_repos)) -> ReleaseNoteService:
    return ReleaseNoteService(repos)


async def get_deprecation_service(repos: RepositoryRegistry = Depends(get_repos)) -> DeprecationService:
    return DeprecationService(repos)


# -- collaboration --------------------------------------------------------------------------------------------
async def get_comment_service(repos: RepositoryRegistry = Depends(get_repos)) -> CommentService:
    return CommentService(repos)


async def get_review_service(repos: RepositoryRegistry = Depends(get_repos)) -> ReviewService:
    return ReviewService(repos)


async def get_audit_log_service(repos: RepositoryRegistry = Depends(get_repos)) -> AuditLogService:
    return AuditLogService(repos)


# -- analytics -------------------------------------------------------------------------------------------------
async def get_analytics_event_service(repos: RepositoryRegistry = Depends(get_repos)) -> AnalyticsEventService:
    return AnalyticsEventService(repos)


async def get_feedback_service(repos: RepositoryRegistry = Depends(get_repos)) -> FeedbackService:
    return FeedbackService(repos)


async def get_broken_link_service(repos: RepositoryRegistry = Depends(get_repos)) -> BrokenLinkService:
    return BrokenLinkService(repos)


async def get_content_freshness_service(repos: RepositoryRegistry = Depends(get_repos)) -> ContentFreshnessService:
    return ContentFreshnessService(repos, get_settings())


# -- security & governance ----------------------------------------------------------------------------------------
async def get_role_assignment_service(repos: RepositoryRegistry = Depends(get_repos)) -> RoleAssignmentService:
    return RoleAssignmentService(repos, get_settings())


async def get_visibility_service(
    role_service: RoleAssignmentService = Depends(get_role_assignment_service),
) -> VisibilityService:
    return VisibilityService(role_service)


def get_governance_service() -> GovernanceService:
    return GovernanceService()
