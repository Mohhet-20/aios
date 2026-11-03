from __future__ import annotations

import enum


class RouteProtocol(str, enum.Enum):
    REST = "rest"
    GRAPHQL = "graphql"
    WEBSOCKET = "websocket"
    SSE = "sse"
    STREAMING = "streaming"
    GRPC = "grpc"


class RouteVisibility(str, enum.Enum):
    INTERNAL = "internal"
    EXTERNAL = "external"
    PUBLIC = "public"
    PRIVATE = "private"
    PARTNER = "partner"
    ADMIN = "admin"


class RouteStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class ApiKeyStatus(str, enum.Enum):
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ApiVersionStatus(str, enum.Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class OAuthClientStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"


class SchemaKind(str, enum.Enum):
    REQUEST = "request"
    RESPONSE = "response"


class ServiceStatus(str, enum.Enum):
    REGISTERED = "registered"
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEREGISTERED = "deregistered"


class InstanceStatus(str, enum.Enum):
    ACTIVE = "active"
    DRAINING = "draining"
    UNHEALTHY = "unhealthy"
    REMOVED = "removed"


class LoadBalancingStrategy(str, enum.Enum):
    ROUND_ROBIN = "round_robin"
    WEIGHTED = "weighted"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"


class CircuitBreakerState(str, enum.Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class TrafficRuleType(str, enum.Enum):
    WEIGHTED = "weighted"
    CANARY = "canary"
    BLUE_GREEN = "blue_green"
    HEADER = "header"
    PATH = "path"
    REGION = "region"
    PRIORITY = "priority"
    MIRROR = "mirror"
    SPLIT = "split"
    FAILOVER = "failover"


class TrafficRuleStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class EventCategory(str, enum.Enum):
    WORKFLOW = "workflow"
    AGENT = "agent"
    PROMPT = "prompt"
    SECURITY = "security"
    SYSTEM = "system"
    CUSTOM = "custom"


class TopicStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    RETIRED = "retired"


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class EventMessageStatus(str, enum.Enum):
    PUBLISHED = "published"
    DELIVERED = "delivered"
    FAILED = "failed"
    DEAD_LETTERED = "dead_lettered"


class ConnectorType(str, enum.Enum):
    CRM = "crm"
    ERP = "erp"
    EMAIL = "email"
    CALENDAR = "calendar"
    CLOUD_STORAGE = "cloud_storage"
    GITHUB = "github"
    GITLAB = "gitlab"
    JIRA = "jira"
    CONFLUENCE = "confluence"
    SLACK = "slack"
    MICROSOFT_TEAMS = "microsoft_teams"
    SALESFORCE = "salesforce"
    SAP = "sap"
    CUSTOM_REST = "custom_rest"
    CUSTOM_GRAPHQL = "custom_graphql"
    CUSTOM_ENTERPRISE = "custom_enterprise"


class ConnectionStatus(str, enum.Enum):
    PENDING = "pending"
    CONNECTED = "connected"
    ERROR = "error"
    DISCONNECTED = "disconnected"


class WebhookSubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class WebhookDeliveryStatus(str, enum.Enum):
    PENDING = "pending"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTERED = "dead_lettered"


class TranslationPair(str, enum.Enum):
    REST_GRAPHQL = "rest_graphql"
    REST_WEBSOCKET = "rest_websocket"
    REST_EVENT_STREAM = "rest_event_stream"


class TranslationConfigStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class SecurityPolicyType(str, enum.Enum):
    IP_FILTER = "ip_filter"
    GEO_RESTRICTION = "geo_restriction"
    RATE_LIMIT = "rate_limit"
    REQUEST_SIGNING = "request_signing"
    BOT_DETECTION = "bot_detection"
    THREAT_DETECTION = "threat_detection"


class SecurityPolicyStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class FilterAction(str, enum.Enum):
    ALLOW = "allow"
    DENY = "deny"


class SecurityEventSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GatewayMetricType(str, enum.Enum):
    API_CALLS = "api_calls"
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    FAILURES = "failures"
    RETRIES = "retries"
    GATEWAY_HEALTH = "gateway_health"
    SERVICE_HEALTH = "service_health"
    TRAFFIC_VOLUME = "traffic_volume"
    ERROR_RATE = "error_rate"


class AnalyticsSnapshotType(str, enum.Enum):
    API_USAGE = "api_usage"
    CONSUMER_ANALYTICS = "consumer_analytics"
    TRAFFIC_TRENDS = "traffic_trends"
    ENDPOINT_PERFORMANCE = "endpoint_performance"
    SERVICE_AVAILABILITY = "service_availability"
    INTEGRATION_HEALTH = "integration_health"
    VERSION_ADOPTION = "version_adoption"
    CAPACITY_TRENDS = "capacity_trends"


class CodeGenLanguage(str, enum.Enum):
    PYTHON = "python"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    CSHARP = "csharp"


class SdkGenStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
