"""Domain exception hierarchy. Every service raises these directly —
the REST layer's exception_handlers.py maps them to HTTP status codes
so no router needs a try/except block."""
from __future__ import annotations


class DocsPlatformError(Exception):
    pass


# -- common ---------------------------------------------------------------------------------------------

class NotFoundError(DocsPlatformError):
    pass


class ValidationError(DocsPlatformError):
    pass


class ConflictError(DocsPlatformError):
    pass


class ConcurrentModificationError(DocsPlatformError):
    pass


class AuthorizationError(DocsPlatformError):
    pass


class PermissionDeniedError(AuthorizationError):
    pass


class TenantIsolationError(AuthorizationError):
    pass


class InvalidTransitionError(DocsPlatformError):
    pass


# -- documentation core -----------------------------------------------------------------------------------

class DocumentationError(DocsPlatformError):
    pass


class DocSpaceNotFoundError(DocumentationError):
    pass


class DocPageNotFoundError(DocumentationError):
    pass


class UnsupportedDocTypeError(DocumentationError):
    pass


# -- API / SDK documentation & automation -------------------------------------------------------------------

class ApiDocError(DocsPlatformError):
    pass


class ApiDocEntryNotFoundError(ApiDocError):
    pass


class UnsupportedApiProtocolError(ApiDocError):
    pass


class SdkDocError(DocsPlatformError):
    pass


class SdkDocEntryNotFoundError(SdkDocError):
    pass


class UnsupportedSdkLanguageError(SdkDocError):
    pass


class GenerationJobError(DocsPlatformError):
    pass


class GenerationJobNotFoundError(GenerationJobError):
    pass


class UnsupportedGenerationJobTypeError(GenerationJobError):
    pass


# -- architecture portal -----------------------------------------------------------------------------------

class ArchitectureError(DocsPlatformError):
    pass


class DiagramNotFoundError(ArchitectureError):
    pass


class UnsupportedDiagramTypeError(ArchitectureError):
    pass


# -- knowledge base -----------------------------------------------------------------------------------------

class KnowledgeBaseError(DocsPlatformError):
    pass


class KbArticleNotFoundError(KnowledgeBaseError):
    pass


class UnsupportedKbArticleTypeError(KnowledgeBaseError):
    pass


# -- learning platform --------------------------------------------------------------------------------------

class LearningError(DocsPlatformError):
    pass


class TutorialNotFoundError(LearningError):
    pass


class LearningPathNotFoundError(LearningError):
    pass


class EnrollmentNotFoundError(LearningError):
    pass


class UnsupportedTutorialTypeError(LearningError):
    pass


# -- AI documentation assistant -----------------------------------------------------------------------------

class AssistantError(DocsPlatformError):
    pass


class AssistantSessionNotFoundError(AssistantError):
    pass


# -- search platform -----------------------------------------------------------------------------------------

class SearchError(DocsPlatformError):
    pass


class InvalidSearchQueryError(SearchError):
    pass


# -- versioning & release notes ---------------------------------------------------------------------------------

class VersioningError(DocsPlatformError):
    pass


class DocVersionNotFoundError(VersioningError):
    pass


class ReleaseNoteNotFoundError(VersioningError):
    pass


# -- collaboration --------------------------------------------------------------------------------------------

class CollaborationError(DocsPlatformError):
    pass


class CommentNotFoundError(CollaborationError):
    pass


class ReviewNotFoundError(CollaborationError):
    pass


class ReviewAlreadyDecidedError(CollaborationError):
    pass


# -- analytics -------------------------------------------------------------------------------------------------

class AnalyticsError(DocsPlatformError):
    pass


class AnalyticsEventNotFoundError(AnalyticsError):
    pass


# -- security & governance ----------------------------------------------------------------------------------------

class GovernanceError(DocsPlatformError):
    pass


class VersionProtectedError(GovernanceError):
    pass
