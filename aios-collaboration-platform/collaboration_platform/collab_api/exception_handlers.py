"""Maps the platform's domain exception hierarchy (core/exceptions.py) to
HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need a
try/except block either. Order matters: this is checked top-to-bottom,
so subclasses are listed before their parent class."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from collaboration_platform.core.exceptions import (
    ApprovalError,
    AssetArchivedError,
    AssetError,
    AuthorizationError,
    BranchError,
    CollaborationPlatformError,
    CommentError,
    CommentTooLongError,
    ConcurrentModificationError,
    ConflictError,
    EditConflictError,
    ExternalSharingDisabledError,
    FolderError,
    InvalidReleaseTagError,
    InvalidTransitionError,
    LibraryError,
    MergeConflictError,
    NotFoundError,
    NotificationError,
    PermissionDeniedError,
    PolicyError,
    PresenceError,
    QuotaExceededError,
    RetentionPolicyError,
    ReviewAlreadyDecidedError,
    ReviewError,
    SearchError,
    ShareLinkExpiredError,
    ShareLinkRevokedError,
    SharingError,
    StaleWriteError,
    ThreadAlreadyResolvedError,
    ValidationError,
    VersionError,
    WorkspaceArchivedError,
    WorkspaceError,
)

_STATUS_BY_EXCEPTION: list[tuple[type[CollaborationPlatformError], int]] = [
    (NotFoundError, 404),
    (CommentTooLongError, 422),
    (ThreadAlreadyResolvedError, 409),
    (CommentError, 400),
    (ReviewAlreadyDecidedError, 409),
    (ReviewError, 400),
    (ApprovalError, 400),
    (PolicyError, 400),
    (InvalidReleaseTagError, 422),
    (MergeConflictError, 409),
    (BranchError, 400),
    (VersionError, 400),
    (StaleWriteError, 409),
    (EditConflictError, 409),
    (PresenceError, 400),
    (WorkspaceArchivedError, 409),
    (WorkspaceError, 400),
    (AssetArchivedError, 409),
    (AssetError, 400),
    (FolderError, 400),
    (LibraryError, 400),
    (SearchError, 400),
    (NotificationError, 400),
    (ShareLinkExpiredError, 410),
    (ShareLinkRevokedError, 410),
    (ExternalSharingDisabledError, 403),
    (SharingError, 400),
    (RetentionPolicyError, 400),
    (QuotaExceededError, 429),
    (PermissionDeniedError, 403),
    (AuthorizationError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (ValidationError, 422),
]


def _status_for(exc: CollaborationPlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(CollaborationPlatformError)
    async def _handle_platform_error(request: Request, exc: CollaborationPlatformError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"error": exc.__class__.__name__, "detail": str(exc)})
