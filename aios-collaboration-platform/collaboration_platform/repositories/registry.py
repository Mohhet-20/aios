"""RepositoryRegistry: wires every repository to one shared AsyncSession,
so a single unit-of-work-scoped session backs every repository an
application-service call touches. Same pattern as every other AIOS
services's `RepositoryRegistry`."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from collaboration_platform.repositories.activity_repository import ActivityEventRepository
from collaboration_platform.repositories.asset_repository import CollaborationAssetRepository
from collaboration_platform.repositories.comment_repository import (
    CommentAttachmentRepository,
    CommentEditHistoryRepository,
    CommentReactionRepository,
    CommentRepository,
    MentionRepository,
)
from collaboration_platform.repositories.governance_repository import (
    AssetPermissionRepository,
    AuditLogEntryRepository,
    ExternalShareRepository,
    RetentionPolicyRepository,
    SharingLinkRepository,
    WorkspacePermissionRepository,
)
from collaboration_platform.repositories.library_repository import LibraryAssetRepository, LibraryFavoriteRepository
from collaboration_platform.repositories.notification_repository import (
    NotificationDeliveryRepository,
    NotificationPreferenceRepository,
    NotificationRepository,
)
from collaboration_platform.repositories.presence_repository import (
    ConflictRecordRepository,
    EditSessionRepository,
    PresenceSessionRepository,
)
from collaboration_platform.repositories.productivity_repository import (
    BookmarkRepository,
    ChecklistItemRepository,
    ChecklistRepository,
    PinnedItemRepository,
    TaskRepository,
)
from collaboration_platform.repositories.review_repository import (
    ApprovalPolicyRepository,
    ReviewAssignmentRepository,
    ReviewRequestRepository,
)
from collaboration_platform.repositories.search_repository import RecentItemRepository, SavedSearchRepository
from collaboration_platform.repositories.version_repository import BranchRepository, MergeRepository, VersionRepository
from collaboration_platform.repositories.workspace_repository import (
    AssetTagRepository,
    CollectionItemRepository,
    CollectionRepository,
    FavoriteRepository,
    FolderRepository,
    ProjectRepository,
    TagRepository,
    WorkspaceMemberRepository,
    WorkspaceRepository,
    WorkspaceTemplateRepository,
)


class RepositoryRegistry:
    """One instance per unit-of-work session; exposes every repository as
    a lazily-constructed, memoized property so services only pay for the
    repositories they actually touch."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self._cache: dict[str, object] = {}

    def _get(self, key: str, cls: type):
        if key not in self._cache:
            self._cache[key] = cls(self.session)
        return self._cache[key]

    # -- workspaces / projects / organization --------------------------------------
    @property
    def workspace_templates(self) -> WorkspaceTemplateRepository:
        return self._get("workspace_templates", WorkspaceTemplateRepository)

    @property
    def workspaces(self) -> WorkspaceRepository:
        return self._get("workspaces", WorkspaceRepository)

    @property
    def workspace_members(self) -> WorkspaceMemberRepository:
        return self._get("workspace_members", WorkspaceMemberRepository)

    @property
    def projects(self) -> ProjectRepository:
        return self._get("projects", ProjectRepository)

    @property
    def folders(self) -> FolderRepository:
        return self._get("folders", FolderRepository)

    @property
    def collections(self) -> CollectionRepository:
        return self._get("collections", CollectionRepository)

    @property
    def collection_items(self) -> CollectionItemRepository:
        return self._get("collection_items", CollectionItemRepository)

    @property
    def tags(self) -> TagRepository:
        return self._get("tags", TagRepository)

    @property
    def asset_tags(self) -> AssetTagRepository:
        return self._get("asset_tags", AssetTagRepository)

    @property
    def favorites(self) -> FavoriteRepository:
        return self._get("favorites", FavoriteRepository)

    # -- collaboration assets ----------------------------------------------------
    @property
    def assets(self) -> CollaborationAssetRepository:
        return self._get("assets", CollaborationAssetRepository)

    # -- real-time collaboration ---------------------------------------------------
    @property
    def presence_sessions(self) -> PresenceSessionRepository:
        return self._get("presence_sessions", PresenceSessionRepository)

    @property
    def edit_sessions(self) -> EditSessionRepository:
        return self._get("edit_sessions", EditSessionRepository)

    @property
    def conflict_records(self) -> ConflictRecordRepository:
        return self._get("conflict_records", ConflictRecordRepository)

    # -- comments / discussions ------------------------------------------------------
    @property
    def comments(self) -> CommentRepository:
        return self._get("comments", CommentRepository)

    @property
    def comment_reactions(self) -> CommentReactionRepository:
        return self._get("comment_reactions", CommentReactionRepository)

    @property
    def comment_attachments(self) -> CommentAttachmentRepository:
        return self._get("comment_attachments", CommentAttachmentRepository)

    @property
    def mentions(self) -> MentionRepository:
        return self._get("mentions", MentionRepository)

    @property
    def comment_edit_history(self) -> CommentEditHistoryRepository:
        return self._get("comment_edit_history", CommentEditHistoryRepository)

    # -- activity ---------------------------------------------------------------------
    @property
    def activity_events(self) -> ActivityEventRepository:
        return self._get("activity_events", ActivityEventRepository)

    # -- notifications ------------------------------------------------------------------
    @property
    def notifications(self) -> NotificationRepository:
        return self._get("notifications", NotificationRepository)

    @property
    def notification_preferences(self) -> NotificationPreferenceRepository:
        return self._get("notification_preferences", NotificationPreferenceRepository)

    @property
    def notification_deliveries(self) -> NotificationDeliveryRepository:
        return self._get("notification_deliveries", NotificationDeliveryRepository)

    # -- version control -------------------------------------------------------------
    @property
    def versions(self) -> VersionRepository:
        return self._get("versions", VersionRepository)

    @property
    def branches(self) -> BranchRepository:
        return self._get("branches", BranchRepository)

    @property
    def merges(self) -> MergeRepository:
        return self._get("merges", MergeRepository)

    # -- reviews / approvals -----------------------------------------------------------
    @property
    def approval_policies(self) -> ApprovalPolicyRepository:
        return self._get("approval_policies", ApprovalPolicyRepository)

    @property
    def review_requests(self) -> ReviewRequestRepository:
        return self._get("review_requests", ReviewRequestRepository)

    @property
    def review_assignments(self) -> ReviewAssignmentRepository:
        return self._get("review_assignments", ReviewAssignmentRepository)

    # -- shared libraries --------------------------------------------------------------
    @property
    def library_assets(self) -> LibraryAssetRepository:
        return self._get("library_assets", LibraryAssetRepository)

    @property
    def library_favorites(self) -> LibraryFavoriteRepository:
        return self._get("library_favorites", LibraryFavoriteRepository)

    # -- search ---------------------------------------------------------------------------
    @property
    def saved_searches(self) -> SavedSearchRepository:
        return self._get("saved_searches", SavedSearchRepository)

    @property
    def recent_items(self) -> RecentItemRepository:
        return self._get("recent_items", RecentItemRepository)

    # -- productivity ------------------------------------------------------------------
    @property
    def tasks(self) -> TaskRepository:
        return self._get("tasks", TaskRepository)

    @property
    def checklists(self) -> ChecklistRepository:
        return self._get("checklists", ChecklistRepository)

    @property
    def checklist_items(self) -> ChecklistItemRepository:
        return self._get("checklist_items", ChecklistItemRepository)

    @property
    def bookmarks(self) -> BookmarkRepository:
        return self._get("bookmarks", BookmarkRepository)

    @property
    def pinned_items(self) -> PinnedItemRepository:
        return self._get("pinned_items", PinnedItemRepository)

    # -- governance / security ------------------------------------------------------------
    @property
    def workspace_permissions(self) -> WorkspacePermissionRepository:
        return self._get("workspace_permissions", WorkspacePermissionRepository)

    @property
    def asset_permissions(self) -> AssetPermissionRepository:
        return self._get("asset_permissions", AssetPermissionRepository)

    @property
    def sharing_links(self) -> SharingLinkRepository:
        return self._get("sharing_links", SharingLinkRepository)

    @property
    def external_shares(self) -> ExternalShareRepository:
        return self._get("external_shares", ExternalShareRepository)

    @property
    def audit_log_entries(self) -> AuditLogEntryRepository:
        return self._get("audit_log_entries", AuditLogEntryRepository)

    @property
    def retention_policies(self) -> RetentionPolicyRepository:
        return self._get("retention_policies", RetentionPolicyRepository)
