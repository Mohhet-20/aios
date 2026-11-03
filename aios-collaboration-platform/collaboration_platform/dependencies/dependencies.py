"""FastAPI dependency wiring: DB session -> RepositoryRegistry -> every
service. Auth is intentionally minimal here, matching every sibling
AIOS platform: this platform expects to sit behind an already-
authenticated gateway (in practice, the Identity Platform) that
forwards the caller's identity via the `X-User-Id` header. Every
service is built fresh per request off a per-request
`RepositoryRegistry`/`AsyncSession`, since a session must never be
shared across concurrent requests."""
from __future__ import annotations

from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from collaboration_platform.activity.activity_service import ActivityService
from collaboration_platform.analytics.observability_service import ObservabilityService
from collaboration_platform.collab_assets.asset_service import CollaborationAssetService
from collaboration_platform.comments.attachment_service import AttachmentService
from collaboration_platform.comments.comment_service import CommentService
from collaboration_platform.comments.reaction_service import ReactionService
from collaboration_platform.config.settings import Settings, get_settings
from collaboration_platform.database.session import session_scope
from collaboration_platform.governance.audit_service import AuditService
from collaboration_platform.governance.permission_service import PermissionService
from collaboration_platform.governance.retention_service import RetentionService
from collaboration_platform.libraries.library_service import LibraryService
from collaboration_platform.mentions.mention_service import MentionService
from collaboration_platform.notifications.digest_service import DigestService
from collaboration_platform.notifications.notification_service import NotificationService
from collaboration_platform.notifications.preference_service import NotificationPreferenceService
from collaboration_platform.productivity.bookmark_service import BookmarkService
from collaboration_platform.productivity.checklist_service import ChecklistService
from collaboration_platform.productivity.pinned_service import PinnedItemService
from collaboration_platform.productivity.task_service import TaskService
from collaboration_platform.projects.collection_service import CollectionService
from collaboration_platform.projects.favorite_service import FavoriteService
from collaboration_platform.projects.folder_service import FolderService
from collaboration_platform.projects.project_service import ProjectService
from collaboration_platform.projects.tag_service import TagService
from collaboration_platform.realtime.conflict_service import ConflictService
from collaboration_platform.realtime.edit_session_service import EditSessionService
from collaboration_platform.realtime.presence_service import PresenceService
from collaboration_platform.realtime.sync_service import SyncService
from collaboration_platform.repositories.registry import RepositoryRegistry
from collaboration_platform.reviews.policy_service import ApprovalPolicyService
from collaboration_platform.reviews.review_service import ReviewService
from collaboration_platform.search.recent_items_service import RecentItemsService
from collaboration_platform.search.saved_search_service import SavedSearchService
from collaboration_platform.search.search_service import SearchService
from collaboration_platform.sharing.sharing_service import ExternalShareService, ShareLinkService
from collaboration_platform.versioning.branch_service import BranchService
from collaboration_platform.versioning.merge_service import MergeService
from collaboration_platform.versioning.version_service import VersionService
from collaboration_platform.workspace.member_service import WorkspaceMemberService
from collaboration_platform.workspace.template_service import WorkspaceTemplateService
from collaboration_platform.workspace.workspace_service import WorkspaceService


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Delegates to `session_scope`, which commits on a clean exit and
    rolls back on any exception — a request handled through the REST
    API needs its writes to actually persist once the response is
    returned (see `database/session.py`'s docstring for the contrast
    with the bare, test-oriented `get_db_session`)."""
    async for session in session_scope():
        yield session


async def get_repos(session: AsyncSession = Depends(get_session)) -> RepositoryRegistry:
    return RepositoryRegistry(session)


def get_settings_dep() -> Settings:
    return get_settings()


async def get_current_actor_id(x_user_id: str | None = Header(default=None)) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id


# -- workspace / projects -----------------------------------------------------------
def get_workspace_service(repos: RepositoryRegistry = Depends(get_repos)) -> WorkspaceService:
    return WorkspaceService(repos)


def get_workspace_member_service(repos: RepositoryRegistry = Depends(get_repos)) -> WorkspaceMemberService:
    return WorkspaceMemberService(repos)


def get_workspace_template_service(repos: RepositoryRegistry = Depends(get_repos)) -> WorkspaceTemplateService:
    return WorkspaceTemplateService(repos)


def get_project_service(repos: RepositoryRegistry = Depends(get_repos)) -> ProjectService:
    return ProjectService(repos)


def get_folder_service(repos: RepositoryRegistry = Depends(get_repos)) -> FolderService:
    return FolderService(repos)


def get_collection_service(repos: RepositoryRegistry = Depends(get_repos)) -> CollectionService:
    return CollectionService(repos)


def get_tag_service(repos: RepositoryRegistry = Depends(get_repos)) -> TagService:
    return TagService(repos)


def get_favorite_service(repos: RepositoryRegistry = Depends(get_repos)) -> FavoriteService:
    return FavoriteService(repos)


def get_asset_service(repos: RepositoryRegistry = Depends(get_repos)) -> CollaborationAssetService:
    return CollaborationAssetService(repos)


# -- real-time -------------------------------------------------------------------------
def get_presence_service(repos: RepositoryRegistry = Depends(get_repos)) -> PresenceService:
    return PresenceService(repos)


def get_edit_session_service(repos: RepositoryRegistry = Depends(get_repos)) -> EditSessionService:
    return EditSessionService(repos)


def get_conflict_service(repos: RepositoryRegistry = Depends(get_repos)) -> ConflictService:
    return ConflictService(repos)


def get_sync_service(repos: RepositoryRegistry = Depends(get_repos)) -> SyncService:
    return SyncService(repos)


# -- comments / mentions ------------------------------------------------------------------
def get_comment_service(repos: RepositoryRegistry = Depends(get_repos)) -> CommentService:
    return CommentService(repos)


def get_reaction_service(repos: RepositoryRegistry = Depends(get_repos)) -> ReactionService:
    return ReactionService(repos)


def get_attachment_service(repos: RepositoryRegistry = Depends(get_repos)) -> AttachmentService:
    return AttachmentService(repos)


def get_mention_service(repos: RepositoryRegistry = Depends(get_repos)) -> MentionService:
    return MentionService(repos)


# -- activity --------------------------------------------------------------------------
def get_activity_service(repos: RepositoryRegistry = Depends(get_repos)) -> ActivityService:
    return ActivityService(repos)


# -- notifications ------------------------------------------------------------------------
def get_notification_service(repos: RepositoryRegistry = Depends(get_repos)) -> NotificationService:
    return NotificationService(repos)


def get_notification_preference_service(repos: RepositoryRegistry = Depends(get_repos)) -> NotificationPreferenceService:
    return NotificationPreferenceService(repos)


def get_digest_service(repos: RepositoryRegistry = Depends(get_repos)) -> DigestService:
    return DigestService(repos)


# -- versioning --------------------------------------------------------------------------
def get_version_service(repos: RepositoryRegistry = Depends(get_repos)) -> VersionService:
    return VersionService(repos)


def get_branch_service(repos: RepositoryRegistry = Depends(get_repos)) -> BranchService:
    return BranchService(repos)


def get_merge_service(repos: RepositoryRegistry = Depends(get_repos)) -> MergeService:
    return MergeService(repos)


# -- reviews / approvals -------------------------------------------------------------------
def get_review_service(repos: RepositoryRegistry = Depends(get_repos)) -> ReviewService:
    return ReviewService(repos)


def get_policy_service(repos: RepositoryRegistry = Depends(get_repos)) -> ApprovalPolicyService:
    return ApprovalPolicyService(repos)


# -- libraries --------------------------------------------------------------------------
def get_library_service(repos: RepositoryRegistry = Depends(get_repos)) -> LibraryService:
    return LibraryService(repos)


# -- search ---------------------------------------------------------------------------
def get_search_service(repos: RepositoryRegistry = Depends(get_repos)) -> SearchService:
    return SearchService(repos)


def get_recent_items_service(repos: RepositoryRegistry = Depends(get_repos)) -> RecentItemsService:
    return RecentItemsService(repos)


def get_saved_search_service(repos: RepositoryRegistry = Depends(get_repos)) -> SavedSearchService:
    return SavedSearchService(repos)


# -- productivity ------------------------------------------------------------------------
def get_task_service(repos: RepositoryRegistry = Depends(get_repos)) -> TaskService:
    return TaskService(repos)


def get_checklist_service(repos: RepositoryRegistry = Depends(get_repos)) -> ChecklistService:
    return ChecklistService(repos)


def get_bookmark_service(repos: RepositoryRegistry = Depends(get_repos)) -> BookmarkService:
    return BookmarkService(repos)


def get_pinned_service(repos: RepositoryRegistry = Depends(get_repos)) -> PinnedItemService:
    return PinnedItemService(repos)


# -- observability -----------------------------------------------------------------------
def get_observability_service(repos: RepositoryRegistry = Depends(get_repos)) -> ObservabilityService:
    return ObservabilityService(repos)


# -- governance / security ------------------------------------------------------------
def get_permission_service(repos: RepositoryRegistry = Depends(get_repos)) -> PermissionService:
    return PermissionService(repos)


def get_share_link_service(repos: RepositoryRegistry = Depends(get_repos)) -> ShareLinkService:
    return ShareLinkService(repos)


def get_external_share_service(repos: RepositoryRegistry = Depends(get_repos)) -> ExternalShareService:
    return ExternalShareService(repos)


def get_audit_service(repos: RepositoryRegistry = Depends(get_repos)) -> AuditService:
    return AuditService(repos)


def get_retention_service(repos: RepositoryRegistry = Depends(get_repos)) -> RetentionService:
    return RetentionService(repos)
