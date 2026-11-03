"""All status/type enums for the Multi-Agent AI Platform domain."""
from __future__ import annotations

from enum import Enum


class AgentCategory(str, Enum):
    """The specialized agent types the platform ships with. New types are
    added by inserting a new AgentTypeModel row, not a new Python class —
    this enum exists for the built-in seed set and for anywhere code needs
    to reason about a *kind* of specialist, not as a closed set."""
    PLANNER = "planner"
    RESEARCH = "research"
    REASONING = "reasoning"
    CRITIC = "critic"
    REVIEWER = "reviewer"
    VERIFIER = "verifier"
    CODING = "coding"
    DOCUMENTATION = "documentation"
    SUMMARIZATION = "summarization"
    RETRIEVAL = "retrieval"
    MEMORY = "memory"
    TOOL = "tool"
    WORKFLOW = "workflow"
    REPORTING = "reporting"
    COORDINATOR = "coordinator"
    HUMAN_APPROVAL = "human_approval"
    SYSTEM = "system"
    CUSTOM = "custom"


class AgentLifecycleStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class AgentHealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class TaskStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class OrchestrationStrategy(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    DYNAMIC = "dynamic"
    CONSENSUS = "consensus"
    SUPERVISOR = "supervisor"
    COLLABORATIVE = "collaborative"


class DelegationStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class MessageType(str, Enum):
    DIRECT = "direct"
    BROADCAST = "broadcast"
    STATUS_UPDATE = "status_update"
    HANDOFF = "handoff"
    EVENT = "event"
    STREAM_CHUNK = "stream_chunk"
    LOG = "log"


class ReasoningMode(str, Enum):
    CHAIN_OF_THOUGHT = "chain_of_thought"
    TREE_OF_THOUGHT = "tree_of_thought"
    REFLECTION = "reflection"
    CRITIQUE = "critique"
    VERIFICATION = "verification"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ExecutionStatus(str, Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


class ToolPermissionLevel(str, Enum):
    NONE = "none"
    READ_ONLY = "read_only"
    EXECUTE = "execute"
    FULL = "full"


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    OPERATOR = "operator"
    VIEWER = "viewer"


class Permission(str, Enum):
    AGENT_CREATE = "agent:create"
    AGENT_READ = "agent:read"
    AGENT_UPDATE = "agent:update"
    AGENT_DELETE = "agent:delete"
    AGENT_EXECUTE = "agent:execute"
    TASK_CREATE = "task:create"
    TASK_READ = "task:read"
    TASK_CANCEL = "task:cancel"
    TASK_APPROVE = "task:approve"
    TOOL_INVOKE = "tool:invoke"
    TOOL_GRANT = "tool:grant"
    DELEGATION_CREATE = "delegation:create"
    AUDIT_READ = "audit:read"
    WORKSPACE_MANAGE = "workspace:manage"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.OWNER: frozenset(Permission),
    Role.ADMIN: frozenset(Permission),
    Role.OPERATOR: frozenset({
        Permission.AGENT_CREATE, Permission.AGENT_READ, Permission.AGENT_UPDATE, Permission.AGENT_EXECUTE,
        Permission.TASK_CREATE, Permission.TASK_READ, Permission.TASK_CANCEL,
        Permission.TOOL_INVOKE, Permission.DELEGATION_CREATE,
    }),
    Role.VIEWER: frozenset({Permission.AGENT_READ, Permission.TASK_READ}),
}


def permissions_for_role(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())
