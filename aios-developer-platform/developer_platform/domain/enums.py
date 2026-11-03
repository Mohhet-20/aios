"""Enum taxonomy for the Enterprise Developer Platform & SDK Ecosystem."""
from __future__ import annotations

import enum


class ApiKeyStatus(str, enum.Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ApiVersionStatus(str, enum.Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"


class SdkLanguage(str, enum.Enum):
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    CSHARP = "csharp"


class CliSessionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"


class ExtensionCategory(str, enum.Enum):
    AGENT = "agent"
    PROMPT = "prompt"
    WORKFLOW = "workflow"
    MEMORY = "memory"
    TOOL = "tool"
    MODEL = "model"
    EVALUATION = "evaluation"
    DASHBOARD = "dashboard"
    AUTHENTICATION = "authentication"
    NOTIFICATION = "notification"
    UI_COMPONENT = "ui_component"


class PluginVersionStatus(str, enum.Enum):
    DRAFT = "draft"
    VALIDATED = "validated"
    SIGNED = "signed"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class MarketplaceReviewStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ExtensionRegistrationStatus(str, enum.Enum):
    REGISTERED = "registered"
    ACTIVE = "active"
    DISABLED = "disabled"


class WebhookDeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    DELIVERING = "delivering"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    EXHAUSTED = "exhausted"


class McpTransport(str, enum.Enum):
    STDIO = "stdio"
    HTTP = "http"
    SSE = "sse"


class McpServerStatus(str, enum.Enum):
    REGISTERED = "registered"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class McpSessionStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CLOSED = "closed"


class CodeGenStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class PortalContentType(str, enum.Enum):
    GETTING_STARTED = "getting_started"
    DOC = "doc"
    TUTORIAL = "tutorial"
    QUICKSTART = "quickstart"
    RELEASE_NOTES = "release_notes"
    MIGRATION_GUIDE = "migration_guide"


class PortalContentStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class SandboxStatus(str, enum.Enum):
    PROVISIONING = "provisioning"
    RUNNING = "running"
    EXPIRED = "expired"
    TERMINATED = "terminated"


class PackageType(str, enum.Enum):
    SDK = "sdk"
    PLUGIN = "plugin"
    WORKFLOW_TEMPLATE = "workflow_template"
    PROMPT_TEMPLATE = "prompt_template"
    AGENT_TEMPLATE = "agent_template"


class PackageVersionStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class UsageEventType(str, enum.Enum):
    SDK_CALL = "sdk_call"
    API_CALL = "api_call"
    CLI_COMMAND = "cli_command"
    PLUGIN_INSTALL = "plugin_install"
    WEBHOOK_DELIVERY = "webhook_delivery"
    DEVELOPER_ACTIVITY = "developer_activity"
    PACKAGE_DOWNLOAD = "package_download"
    API_ERROR = "api_error"


class DeveloperRole(str, enum.Enum):
    """Ordered — deliberately smaller than the Identity Platform's
    fine-grained resource_type:action grammar, matching the precedent
    set by every sibling AIOS platform's own RBAC."""
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"

    @property
    def rank(self) -> int:
        return {"viewer": 0, "operator": 1, "admin": 2}[self.value]


class SecretReferenceType(str, enum.Enum):
    WEBHOOK_SECRET = "webhook_secret"
    API_CREDENTIAL = "api_credential"
    PLUGIN_SECRET = "plugin_secret"
