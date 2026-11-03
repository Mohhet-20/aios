"""Exception hierarchy for the Enterprise Collaboration & Workspace
Platform."""
from __future__ import annotations


class CollaborationPlatformError(Exception):
    """Base class for every platform exception."""


class NotFoundError(CollaborationPlatformError):
    pass


class ValidationError(CollaborationPlatformError):
    pass


class ConflictError(CollaborationPlatformError):
    pass


class ConcurrentModificationError(CollaborationPlatformError):
    pass


class AuthorizationError(CollaborationPlatformError):
    pass


class PermissionDeniedError(AuthorizationError):
    pass


class InvalidTransitionError(CollaborationPlatformError):
    """Raised on an illegal lifecycle transition (workspace, comment
    thread, version, review request, notification, etc.)."""


# -- workspaces / projects -----------------------------------------------------------

class WorkspaceError(CollaborationPlatformError):
    pass


class WorkspaceArchivedError(WorkspaceError):
    pass


class ProjectError(CollaborationPlatformError):
    pass


class FolderError(CollaborationPlatformError):
    pass


class QuotaExceededError(CollaborationPlatformError):
    pass


# -- assets ----------------------------------------------------------------------------

class AssetError(CollaborationPlatformError):
    pass


class AssetArchivedError(AssetError):
    pass


# -- real-time collaboration --------------------------------------------------------

class PresenceError(CollaborationPlatformError):
    pass


class EditConflictError(CollaborationPlatformError):
    """Raised when two concurrent edits to the same asset/version base
    cannot be reconciled automatically and need caller-driven resolution."""


class StaleWriteError(EditConflictError):
    """Raised when a write targets a version/etag that is no longer current."""


# -- comments / mentions --------------------------------------------------------------

class CommentError(CollaborationPlatformError):
    pass


class CommentTooLongError(CommentError):
    pass


class ThreadAlreadyResolvedError(CommentError):
    pass


# -- notifications ----------------------------------------------------------------------

class NotificationError(CollaborationPlatformError):
    pass


# -- versioning --------------------------------------------------------------------------

class VersionError(CollaborationPlatformError):
    pass


class BranchError(CollaborationPlatformError):
    pass


class MergeConflictError(VersionError):
    pass


class InvalidReleaseTagError(VersionError):
    pass


# -- reviews / approvals ------------------------------------------------------------------

class ReviewError(CollaborationPlatformError):
    pass


class ApprovalError(CollaborationPlatformError):
    pass


class ReviewAlreadyDecidedError(ReviewError):
    pass


class PolicyError(CollaborationPlatformError):
    pass


# -- libraries --------------------------------------------------------------------------

class LibraryError(CollaborationPlatformError):
    pass


# -- search ---------------------------------------------------------------------------

class SearchError(CollaborationPlatformError):
    pass


# -- sharing / governance ----------------------------------------------------------------

class SharingError(CollaborationPlatformError):
    pass


class ShareLinkExpiredError(SharingError):
    pass


class ShareLinkRevokedError(SharingError):
    pass


class ExternalSharingDisabledError(SharingError):
    pass


class RetentionPolicyError(CollaborationPlatformError):
    pass
