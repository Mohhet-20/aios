"""Enum vocabulary for the docs platform. `JobStatus` is shared across
every job/run-style resource (generation jobs) — reused rather than
re-declared per module, since the transition semantics are identical,
the same precedent set in the Quality Platform (Phase 19)."""
from __future__ import annotations

import enum


class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# -- documentation core ------------------------------------------------------------------------------------

class DocType(str, enum.Enum):
    ARCHITECTURE = "architecture"
    BACKEND = "backend"
    FRONTEND = "frontend"
    API = "api"
    SDK = "sdk"
    WORKFLOW = "workflow"
    AGENT = "agent"
    PROMPT = "prompt"
    KNOWLEDGE = "knowledge"
    INFRASTRUCTURE = "infrastructure"
    DEPLOYMENT = "deployment"
    SECURITY = "security"
    DEVELOPER = "developer"
    ADMIN = "admin"
    ENTERPRISE_CUSTOMER = "enterprise_customer"


class DocPageStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class VisibilityLevel(str, enum.Enum):
    INTERNAL = "internal"
    PUBLIC = "public"


# -- API / SDK documentation & automation --------------------------------------------------------------------

class ApiProtocolType(str, enum.Enum):
    REST = "rest"
    GRAPHQL = "graphql"
    WEBSOCKET = "websocket"
    STREAMING = "streaming"


class SdkLanguage(str, enum.Enum):
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    CSHARP = "csharp"
    CLI = "cli"
    PLUGIN_SDK = "plugin_sdk"
    EXTENSION_SDK = "extension_sdk"
    WEBHOOK_SDK = "webhook_sdk"
    MCP_SDK = "mcp_sdk"


class GenerationJobType(str, enum.Enum):
    API_DOCS = "api_docs"
    SCHEMA_DOCS = "schema_docs"
    CONFIG_DOCS = "config_docs"
    SDK_DOCS = "sdk_docs"
    CHANGELOG = "changelog"
    DEPENDENCY_REPORT = "dependency_report"
    ARCHITECTURE_REPORT = "architecture_report"
    CODE_REFERENCE = "code_reference"


# -- architecture portal -----------------------------------------------------------------------------------------

class DiagramType(str, enum.Enum):
    SYSTEM_OVERVIEW = "system_overview"
    SEQUENCE = "sequence"
    COMPONENT = "component"
    DEPLOYMENT = "deployment"
    INFRASTRUCTURE_MAP = "infrastructure_map"
    SERVICE_MAP = "service_map"
    DEPENDENCY_GRAPH = "dependency_graph"


# -- knowledge base -------------------------------------------------------------------------------------------------

class KbArticleType(str, enum.Enum):
    HOW_TO = "how_to"
    BEST_PRACTICE = "best_practice"
    TROUBLESHOOTING = "troubleshooting"
    FAQ = "faq"
    RELEASE_NOTE = "release_note"
    MIGRATION_GUIDE = "migration_guide"
    DESIGN_PATTERN = "design_pattern"
    REFERENCE = "reference"
    GLOSSARY = "glossary"


class KbArticleStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# -- learning platform ------------------------------------------------------------------------------------------------

class TutorialType(str, enum.Enum):
    GETTING_STARTED = "getting_started"
    INTERACTIVE_TUTORIAL = "interactive_tutorial"
    HANDS_ON_LAB = "hands_on_lab"
    STEP_BY_STEP_GUIDE = "step_by_step_guide"


class LearningRole(str, enum.Enum):
    ADMINISTRATOR = "administrator"
    DEVELOPER = "developer"
    ENTERPRISE_CUSTOMER = "enterprise_customer"


class EnrollmentStatus(str, enum.Enum):
    ENROLLED = "enrolled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


# -- versioning & release notes --------------------------------------------------------------------------------------

class ReleaseNoteKind(str, enum.Enum):
    FEATURE = "feature"
    FIX = "fix"
    BREAKING_CHANGE = "breaking_change"
    DEPRECATION = "deprecation"
    SECURITY = "security"


# -- collaboration --------------------------------------------------------------------------------------------------------

class ReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    CHANGES_REQUESTED = "changes_requested"
    REJECTED = "rejected"


class ContributorRole(str, enum.Enum):
    VIEWER = "viewer"
    CONTRIBUTOR = "contributor"
    EDITOR = "editor"
    OWNER = "owner"
    ADMIN = "admin"


# -- analytics --------------------------------------------------------------------------------------------------------------

class AnalyticsEventType(str, enum.Enum):
    PAGE_VIEW = "page_view"
    SEARCH_QUERY = "search_query"
    TUTORIAL_COMPLETION = "tutorial_completion"
    FEEDBACK = "feedback"
    BROKEN_LINK = "broken_link"
