"""Importing this package populates `Base.metadata` with every ORM
model — required once at process/test startup before `init_models()`."""
from collaboration_platform.models.activity import ActivityEventModel
from collaboration_platform.models.asset import CollaborationAssetModel
from collaboration_platform.models.comment import (
    CommentAttachmentModel,
    CommentEditHistoryModel,
    CommentModel,
    CommentReactionModel,
    MentionModel,
)
from collaboration_platform.models.governance import (
    AssetPermissionModel,
    AuditLogEntryModel,
    ExternalShareModel,
    RetentionPolicyModel,
    SharingLinkModel,
    WorkspacePermissionModel,
)
from collaboration_platform.models.library import LibraryAssetModel, LibraryFavoriteModel
from collaboration_platform.models.notification import (
    NotificationDeliveryModel,
    NotificationModel,
    NotificationPreferenceModel,
)
from collaboration_platform.models.presence import ConflictRecordModel, EditSessionModel, PresenceSessionModel
from collaboration_platform.models.productivity import (
    BookmarkModel,
    ChecklistItemModel,
    ChecklistModel,
    PinnedItemModel,
    TaskModel,
)
from collaboration_platform.models.review import ApprovalPolicyModel, ReviewAssignmentModel, ReviewRequestModel
from collaboration_platform.models.search import RecentItemModel, SavedSearchModel
from collaboration_platform.models.version import BranchModel, MergeModel, VersionModel
from collaboration_platform.models.workspace import (
    AssetTagModel,
    CollectionItemModel,
    CollectionModel,
    FavoriteModel,
    FolderModel,
    ProjectModel,
    TagModel,
    WorkspaceMemberModel,
    WorkspaceModel,
    WorkspaceTemplateModel,
)

__all__ = [
    "ActivityEventModel", "CollaborationAssetModel",
    "CommentAttachmentModel", "CommentEditHistoryModel", "CommentModel", "CommentReactionModel", "MentionModel",
    "AssetPermissionModel", "AuditLogEntryModel", "ExternalShareModel", "RetentionPolicyModel",
    "SharingLinkModel", "WorkspacePermissionModel",
    "LibraryAssetModel", "LibraryFavoriteModel",
    "NotificationDeliveryModel", "NotificationModel", "NotificationPreferenceModel",
    "ConflictRecordModel", "EditSessionModel", "PresenceSessionModel",
    "BookmarkModel", "ChecklistItemModel", "ChecklistModel", "PinnedItemModel", "TaskModel",
    "ApprovalPolicyModel", "ReviewAssignmentModel", "ReviewRequestModel",
    "RecentItemModel", "SavedSearchModel",
    "BranchModel", "MergeModel", "VersionModel",
    "AssetTagModel", "CollectionItemModel", "CollectionModel", "FavoriteModel", "FolderModel",
    "ProjectModel", "TagModel", "WorkspaceMemberModel", "WorkspaceModel", "WorkspaceTemplateModel",
]
