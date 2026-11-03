"""Enumerations shared across the domain, ORM, and service layers."""
from __future__ import annotations

import enum


class LogLevel(str, enum.Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @property
    def severity_rank(self) -> int:
        return {"debug": 0, "info": 1, "warning": 2, "error": 3, "critical": 4}[self.value]


class ComponentType(str, enum.Enum):
    APPLICATION = "application"
    MICROSERVICE = "microservice"
    AGENT = "agent"
    WORKFLOW = "workflow"
    MODEL = "model"
    PROMPT_PLATFORM = "prompt_platform"
    MEMORY_PLATFORM = "memory_platform"
    TOOL_PLATFORM = "tool_platform"
    AUTHENTICATION = "authentication"
    API_GATEWAY = "api_gateway"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    WORKER = "worker"
    STORAGE = "storage"
    EXTERNAL_SERVICE = "external_service"


class MetricType(str, enum.Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class SpanKind(str, enum.Enum):
    INTERNAL = "internal"
    SERVER = "server"
    CLIENT = "client"
    PRODUCER = "producer"
    CONSUMER = "consumer"
    DATABASE_QUERY = "database_query"
    EXTERNAL_CALL = "external_call"
    TOOL_CALL = "tool_call"
    AGENT_EXECUTION = "agent_execution"
    WORKFLOW_STEP = "workflow_step"


class SpanStatus(str, enum.Enum):
    UNSET = "unset"
    OK = "ok"
    ERROR = "error"


class HealthStatus(str, enum.Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

    @property
    def rank(self) -> int:
        """Higher is worse — used to roll many component statuses up into
        one overall system status by taking the max rank."""
        return {"healthy": 0, "unknown": 1, "degraded": 2, "unhealthy": 3}[self.value]


class AlertType(str, enum.Enum):
    THRESHOLD = "threshold"
    ANOMALY = "anomaly"
    AVAILABILITY = "availability"
    LATENCY = "latency"
    RESOURCE = "resource"
    SECURITY = "security"
    WORKFLOW_FAILURE = "workflow_failure"
    AGENT_FAILURE = "agent_failure"
    MEMORY_FAILURE = "memory_failure"
    DATABASE = "database"
    CUSTOM = "custom"


class AlertSeverity(str, enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertStatus(str, enum.Enum):
    FIRING = "firing"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class MaintenanceWindowStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class IncidentSeverity(str, enum.Enum):
    SEV1 = "sev1"  # critical, full outage
    SEV2 = "sev2"  # major functionality impaired
    SEV3 = "sev3"  # minor impact
    SEV4 = "sev4"  # cosmetic / low urgency


class IncidentStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    CLOSED = "closed"


class CapacityResourceType(str, enum.Enum):
    STORAGE = "storage"
    TRAFFIC = "traffic"
    CPU = "cpu"
    MEMORY = "memory"
    COST = "cost"
    CONCURRENT_USERS = "concurrent_users"


class DependencyEdgeType(str, enum.Enum):
    SERVICE = "service"
    WORKFLOW = "workflow"
    AGENT = "agent"
    TOOL = "tool"
    EXTERNAL_INTEGRATION = "external_integration"
    INFRASTRUCTURE = "infrastructure"


class DashboardType(str, enum.Enum):
    EXECUTIVE = "executive"
    OPERATIONS = "operations"
    INFRASTRUCTURE = "infrastructure"
    APPLICATION = "application"
    AI_PLATFORM = "ai_platform"
    WORKFLOW = "workflow"
    DATABASE = "database"
    SECURITY = "security"
    INCIDENT = "incident"
    CAPACITY = "capacity"


class ReportType(str, enum.Enum):
    AVAILABILITY = "availability"
    PERFORMANCE = "performance"
    INCIDENT = "incident"
    SLA = "sla"
    ERROR = "error"
    CAPACITY = "capacity"
    USAGE = "usage"
    TREND = "trend"
    COMPLIANCE = "compliance"


class ReportStatus(str, enum.Enum):
    PENDING = "pending"
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class ObservabilityRole(str, enum.Enum):
    """Ordered — deliberately smaller than the Identity Platform's
    fine-grained resource_type:action grammar. This platform only needs
    to answer "can this principal view telemetry / operate on alerts &
    incidents / administer rules & retention," not a general-purpose
    permission system (that engine already exists one layer down)."""
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"

    @property
    def rank(self) -> int:
        return {"viewer": 0, "operator": 1, "admin": 2}[self.value]


def role_at_least(role: ObservabilityRole, minimum: ObservabilityRole) -> bool:
    return role.rank >= minimum.rank


class NotificationChannelType(str, enum.Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    PAGERDUTY = "pagerduty"
    SMS = "sms"


class NotificationDeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
