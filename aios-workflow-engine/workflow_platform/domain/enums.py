"""Domain enums for the Workflow Orchestration Engine.

Two deliberately orthogonal axes recur throughout this schema, the same
lesson every prior AIOS platform in this series learned the hard way:
`NodeType` (what kind of step) is independent of a workflow's
`WorkflowCategory` (what kind of business process it represents) — a
RESEARCH workflow and a DOCUMENT_PROCESSING workflow can both use an
AGENT node. Likewise `VariableModel` (persistent, workspace/global-scoped
state) is orthogonal to `ExecutionModel.context_variables` (ephemeral,
single-run state) — see `state/` for how the two compose.
"""
from __future__ import annotations

from enum import Enum


class WorkflowCategory(str, Enum):
    AI_AGENT = "ai_agent"
    RESEARCH = "research"
    DOCUMENT_PROCESSING = "document_processing"
    PROMPT_PIPELINE = "prompt_pipeline"
    APPROVAL = "approval"
    DATA_PROCESSING = "data_processing"
    ETL = "etl"
    KNOWLEDGE_PIPELINE = "knowledge_pipeline"
    MODEL_INFERENCE = "model_inference"
    AUTOMATION = "automation"
    NOTIFICATION = "notification"
    API_INTEGRATION = "api_integration"
    SCHEDULED_JOB = "scheduled_job"
    BATCH_PROCESSING = "batch_processing"
    STREAMING_PIPELINE = "streaming_pipeline"
    EVENT_DRIVEN = "event_driven"


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"
    DEPRECATED = "deprecated"


class WorkflowPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class WorkflowVersionStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class NodeType(str, Enum):
    START = "start"
    END = "end"
    AGENT = "agent"
    PROMPT = "prompt"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    RETRIEVER = "retriever"
    KNOWLEDGE_SEARCH = "knowledge_search"
    DECISION = "decision"
    CONDITION = "condition"
    LOOP = "loop"
    PARALLEL_BRANCH = "parallel_branch"
    MERGE = "merge"
    DELAY = "delay"
    WAIT = "wait"
    APPROVAL = "approval"
    NOTIFICATION = "notification"
    WEBHOOK = "webhook"
    REST_API = "rest_api"
    DATABASE_QUERY = "database_query"
    PYTHON_EXECUTION = "python_execution"
    FILE_UPLOAD = "file_upload"
    FILE_PROCESSING = "file_processing"
    DOCUMENT_PARSER = "document_parser"
    EMBEDDING_GENERATOR = "embedding_generator"
    LLM_CALL = "llm_call"
    FUNCTION_CALL = "function_call"
    ERROR_HANDLER = "error_handler"
    RETRY = "retry"
    CUSTOM = "custom"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    COMPENSATING = "compensating"
    COMPENSATED = "compensated"
    TIMED_OUT = "timed_out"


class NodeExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ScheduleType(str, Enum):
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    RECURRING = "recurring"
    CRON = "cron"
    CALENDAR = "calendar"


class ScheduleStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EventType(str, Enum):
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    WORKFLOW_FAILED = "workflow_failed"
    WORKFLOW_CANCELLED = "workflow_cancelled"
    WORKFLOW_PAUSED = "workflow_paused"
    WORKFLOW_RESUMED = "workflow_resumed"
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    NODE_RETRYING = "node_retrying"
    AGENT_EVENT = "agent_event"
    MEMORY_EVENT = "memory_event"
    TOOL_EVENT = "tool_event"
    EXTERNAL_EVENT = "external_event"
    APPROVAL_REQUESTED = "approval_requested"
    APPROVAL_DECIDED = "approval_decided"
    SCHEDULE_TRIGGERED = "schedule_triggered"
    WEBHOOK_RECEIVED = "webhook_received"
    CUSTOM = "custom"


class TriggerType(str, Enum):
    MANUAL = "manual"
    SCHEDULE = "schedule"
    WEBHOOK = "webhook"
    EVENT = "event"
    API = "api"


class VariableScope(str, Enum):
    WORKFLOW = "workflow"
    EXECUTION = "execution"
    WORKSPACE = "workspace"
    GLOBAL = "global"


class SubscriptionTargetType(str, Enum):
    WEBHOOK = "webhook"
    INTERNAL_HANDLER = "internal_handler"


class WebhookDeliveryStatus(str, Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"


class LogLevel(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Permission(str, Enum):
    WORKFLOW_READ = "workflow:read"
    WORKFLOW_WRITE = "workflow:write"
    WORKFLOW_DELETE = "workflow:delete"
    WORKFLOW_EXECUTE = "workflow:execute"
    EXECUTION_READ = "execution:read"
    EXECUTION_CONTROL = "execution:control"
    APPROVAL_DECIDE = "approval:decide"
    SCHEDULE_MANAGE = "schedule:manage"
    NODE_MANAGE = "node:manage"
    AUDIT_READ = "audit:read"
    WORKSPACE_MANAGE = "workspace:manage"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.OWNER: frozenset(Permission),
    Role.ADMIN: frozenset({
        Permission.WORKFLOW_READ, Permission.WORKFLOW_WRITE, Permission.WORKFLOW_DELETE, Permission.WORKFLOW_EXECUTE,
        Permission.EXECUTION_READ, Permission.EXECUTION_CONTROL, Permission.APPROVAL_DECIDE, Permission.SCHEDULE_MANAGE,
        Permission.NODE_MANAGE, Permission.AUDIT_READ,
    }),
    Role.OPERATOR: frozenset({
        Permission.WORKFLOW_READ, Permission.WORKFLOW_WRITE, Permission.WORKFLOW_EXECUTE,
        Permission.EXECUTION_READ, Permission.EXECUTION_CONTROL, Permission.APPROVAL_DECIDE, Permission.SCHEDULE_MANAGE,
    }),
    Role.VIEWER: frozenset({Permission.WORKFLOW_READ, Permission.EXECUTION_READ}),
}


def permissions_for_role(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())
