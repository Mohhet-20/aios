"""Maps the platform's domain exception hierarchy (core/exceptions.py)
to HTTP status codes, so every service can keep raising plain Python
exceptions without knowing anything about HTTP — routers never need a
try/except block either. Order matters: this is checked top-to-bottom,
so subclasses are listed before their parent class."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from docs_platform.core.exceptions import (
    AnalyticsError,
    AnalyticsEventNotFoundError,
    ApiDocEntryNotFoundError,
    ApiDocError,
    ArchitectureError,
    AssistantError,
    AssistantSessionNotFoundError,
    AuthorizationError,
    CollaborationError,
    CommentNotFoundError,
    ConcurrentModificationError,
    ConflictError,
    DiagramNotFoundError,
    DocPageNotFoundError,
    DocSpaceNotFoundError,
    DocsPlatformError,
    DocumentationError,
    DocVersionNotFoundError,
    EnrollmentNotFoundError,
    GenerationJobError,
    GenerationJobNotFoundError,
    GovernanceError,
    InvalidSearchQueryError,
    InvalidTransitionError,
    KbArticleNotFoundError,
    KnowledgeBaseError,
    LearningError,
    LearningPathNotFoundError,
    NotFoundError,
    PermissionDeniedError,
    ReleaseNoteNotFoundError,
    ReviewAlreadyDecidedError,
    ReviewNotFoundError,
    SdkDocEntryNotFoundError,
    SdkDocError,
    SearchError,
    TenantIsolationError,
    TutorialNotFoundError,
    UnsupportedApiProtocolError,
    UnsupportedDiagramTypeError,
    UnsupportedDocTypeError,
    UnsupportedGenerationJobTypeError,
    UnsupportedKbArticleTypeError,
    UnsupportedSdkLanguageError,
    UnsupportedTutorialTypeError,
    ValidationError,
    VersioningError,
    VersionProtectedError,
)

_STATUS_BY_EXCEPTION: list[tuple[type[DocsPlatformError], int]] = [
    (NotFoundError, 404),
    # documentation core
    (DocSpaceNotFoundError, 404),
    (DocPageNotFoundError, 404),
    (UnsupportedDocTypeError, 422),
    (DocumentationError, 400),
    # API / SDK documentation & automation
    (ApiDocEntryNotFoundError, 404),
    (UnsupportedApiProtocolError, 422),
    (ApiDocError, 400),
    (SdkDocEntryNotFoundError, 404),
    (UnsupportedSdkLanguageError, 422),
    (SdkDocError, 400),
    (GenerationJobNotFoundError, 404),
    (UnsupportedGenerationJobTypeError, 422),
    (GenerationJobError, 400),
    # architecture portal
    (DiagramNotFoundError, 404),
    (UnsupportedDiagramTypeError, 422),
    (ArchitectureError, 400),
    # knowledge base
    (KbArticleNotFoundError, 404),
    (UnsupportedKbArticleTypeError, 422),
    (KnowledgeBaseError, 400),
    # learning platform
    (TutorialNotFoundError, 404),
    (LearningPathNotFoundError, 404),
    (EnrollmentNotFoundError, 404),
    (UnsupportedTutorialTypeError, 422),
    (LearningError, 400),
    # AI documentation assistant
    (AssistantSessionNotFoundError, 404),
    (AssistantError, 400),
    # search platform
    (InvalidSearchQueryError, 422),
    (SearchError, 400),
    # versioning & release notes
    (DocVersionNotFoundError, 404),
    (ReleaseNoteNotFoundError, 404),
    (VersioningError, 400),
    # collaboration
    (CommentNotFoundError, 404),
    (ReviewAlreadyDecidedError, 409),
    (ReviewNotFoundError, 404),
    (CollaborationError, 400),
    # analytics
    (AnalyticsEventNotFoundError, 404),
    (AnalyticsError, 400),
    # security & governance
    (VersionProtectedError, 409),
    (GovernanceError, 400),
    # common group
    (TenantIsolationError, 403),
    (PermissionDeniedError, 403),
    (AuthorizationError, 403),
    (ConflictError, 409),
    (ConcurrentModificationError, 409),
    (InvalidTransitionError, 409),
    (ValidationError, 422),
]


def _status_for(exc: DocsPlatformError) -> int:
    for exc_type, status_code in _STATUS_BY_EXCEPTION:
        if isinstance(exc, exc_type):
            return status_code
    return 400


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DocsPlatformError)
    async def _handle_platform_error(request: Request, exc: DocsPlatformError) -> JSONResponse:
        return JSONResponse(status_code=_status_for(exc), content={"error": exc.__class__.__name__, "detail": str(exc)})
