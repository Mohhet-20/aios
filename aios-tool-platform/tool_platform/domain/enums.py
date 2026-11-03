"""Every enum shared across the Tool Execution & Integration Platform.

Two orthogonality notes worth flagging up front (the same class of
"don't conflate these" note the Workflow Engine's enums module carries):

`ToolCategory` vs `capabilities` — category is *what kind* of tool this
is (github, slack, sql, python_execution, ...), a closed, curated list
used for browsing/filtering in the registry and marketplace. Capabilities
(stored as a free-form JSON string list on `ToolVersionModel`, not an
enum here) are *what the tool can do* — "read_file", "sends_email",
"network_access", "code_execution" — used by AI Tool Planning's
capability matching. A single category can imply several capabilities,
and two tools in the same category can have different capability sets
(e.g. a read-only vs. a read-write GitHub connector).

`ExecutionMode` vs `ExecutionStatus` — mode is *how* a call was invoked
(sync/async/streaming/batch/parallel/queued/scheduled), status is
*where it is* in its lifecycle (pending -> running -> succeeded, etc.).
A single execution has exactly one of each, set independently.
"""
from __future__ import annotations

from enum import Enum


class ToolCategory(str, Enum):
    WEB_SEARCH = "web_search"
    HTTP_CLIENT = "http_client"
    REST_API = "rest_api"
    GRAPHQL_API = "graphql_api"
    PYTHON_EXECUTION = "python_execution"
    SHELL_COMMAND = "shell_command"
    FILE_MANAGER = "file_manager"
    PDF_READER = "pdf_reader"
    WORD_READER = "word_reader"
    EXCEL_READER = "excel_reader"
    CSV_PROCESSOR = "csv_processor"
    IMAGE_PROCESSING = "image_processing"
    OCR = "ocr"
    AUDIO_PROCESSING = "audio_processing"
    VIDEO_PROCESSING = "video_processing"
    DOCUMENT_PARSER = "document_parser"
    EMBEDDING_GENERATOR = "embedding_generator"
    DATABASE_QUERY = "database_query"
    SQL = "sql"
    NOSQL = "nosql"
    VECTOR_DATABASE = "vector_database"
    KNOWLEDGE_GRAPH = "knowledge_graph"
    EMAIL = "email"
    CALENDAR = "calendar"
    NOTIFICATION = "notification"
    CLOUD_STORAGE = "cloud_storage"
    GITHUB = "github"
    GITLAB = "gitlab"
    SLACK = "slack"
    DISCORD = "discord"
    JIRA = "jira"
    CONFLUENCE = "confluence"
    CRM = "crm"
    ERP = "erp"
    CUSTOM_ENTERPRISE_API = "custom_enterprise_api"
    MCP_SERVER = "mcp_server"
    CUSTOM = "custom"


class ToolStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


class ToolVersionStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class ToolHealth(str, Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ExecutionMode(str, Enum):
    SYNC = "sync"
    ASYNC = "async"
    STREAMING = "streaming"
    BATCH = "batch"
    PARALLEL = "parallel"
    QUEUED = "queued"
    SCHEDULED = "scheduled"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    RETRYING = "retrying"
    ROLLED_BACK = "rolled_back"

    def is_terminal(self) -> bool:
        return self in {ExecutionStatus.SUCCEEDED, ExecutionStatus.CANCELLED, ExecutionStatus.ROLLED_BACK}


class CredentialType(str, Enum):
    API_KEY = "api_key"
    OAUTH2 = "oauth2"
    JWT = "jwt"
    BEARER_TOKEN = "bearer_token"
    SERVICE_ACCOUNT = "service_account"
    MANAGED = "managed"


class CredentialStatus(str, Enum):
    ACTIVE = "active"
    ROTATING = "rotating"
    EXPIRED = "expired"
    REVOKED = "revoked"


class PluginStatus(str, Enum):
    """Marketplace-listing lifecycle for the `PluginModel` itself (the
    thing you'd browse), as distinct from `PluginInstallationStatus`
    (a specific workspace's copy of it)."""
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    SUSPENDED = "suspended"


class PluginInstallationStatus(str, Enum):
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    UPDATING = "updating"
    FAILED = "failed"
    UNINSTALLED = "uninstalled"


class ScheduleType(str, Enum):
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    CALENDAR = "calendar"
    RECURRING = "recurring"
    CRON = "cron"


class ScheduleStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class SandboxNetworkPolicy(str, Enum):
    DENY_ALL = "deny_all"
    ALLOW_LIST = "allow_list"
    ALLOW_ALL = "allow_all"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ToolSensitivity(str, Enum):
    """Drives approval-gating in `ai_planning`/`tool_execution`: a tool
    marked HIGH or CRITICAL requires a resolved `ApprovalRequiredError`
    escape hatch (an external approval, mirroring the Workflow Engine's
    APPROVAL node) before the engine will actually invoke it."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Permission(str, Enum):
    TOOL_READ = "tool:read"
    TOOL_WRITE = "tool:write"
    TOOL_DELETE = "tool:delete"
    TOOL_EXECUTE = "tool:execute"
    TOOL_EXECUTE_SENSITIVE = "tool:execute_sensitive"
    CREDENTIAL_READ = "credential:read"
    CREDENTIAL_WRITE = "credential:write"
    PLUGIN_INSTALL = "plugin:install"
    PLUGIN_ADMIN = "plugin:admin"
    SCHEDULE_MANAGE = "schedule:manage"
    GOVERNANCE_ADMIN = "governance:admin"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.VIEWER: frozenset({Permission.TOOL_READ, Permission.CREDENTIAL_READ}),
    Role.OPERATOR: frozenset({
        Permission.TOOL_READ, Permission.TOOL_EXECUTE, Permission.CREDENTIAL_READ, Permission.SCHEDULE_MANAGE,
    }),
    Role.ADMIN: frozenset({
        Permission.TOOL_READ, Permission.TOOL_WRITE, Permission.TOOL_DELETE, Permission.TOOL_EXECUTE,
        Permission.TOOL_EXECUTE_SENSITIVE, Permission.CREDENTIAL_READ, Permission.CREDENTIAL_WRITE,
        Permission.PLUGIN_INSTALL, Permission.SCHEDULE_MANAGE,
    }),
    Role.OWNER: frozenset(Permission),
}


def permissions_for_role(role: Role | str) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[Role(role)]
