"""Shared status/type enums used across entities, ORM models, and Pydantic
schemas. Defined once in the domain layer so persistence and API layers both
import the same source of truth instead of redefining string literals.
"""

from enum import Enum


class AgentStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    ERROR = "error"
    TRAINING = "training"
    ARCHIVED = "archived"


class PromptStatus(str, Enum):
    DRAFT = "draft"
    STAGED = "staged"
    PRODUCTION = "production"
    ARCHIVED = "archived"


class WorkflowStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    PAUSED = "paused"
    ARCHIVED = "archived"


class ExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_HUMAN = "waiting_for_human"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EvaluationStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MemoryType(str, Enum):
    SESSION = "session"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"


class NotificationType(str, Enum):
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class AuditStatus(str, Enum):
    SUCCESS = "success"
    FAILED = "failed"


class ToolSideEffect(str, Enum):
    READ_ONLY = "read_only"
    MUTATING = "mutating"


class DatasetType(str, Enum):
    GOLDEN = "golden"
    TRAINING = "training"
    REFERENCE = "reference"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXED = "indexed"
    FAILED = "failed"


class PlanTier(str, Enum):
    STARTER = "starter"
    TEAM = "team"
    ENTERPRISE = "enterprise"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRYING = "retrying"


class ModelModality(str, Enum):
    TEXT = "text"
    VISION = "vision"
    AUDIO = "audio"


class ModelStatus(str, Enum):
    AVAILABLE = "available"
    BETA = "beta"
    DEPRECATED = "deprecated"
