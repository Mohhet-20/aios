"""Enum taxonomy for the Enterprise Analytics, Business Intelligence &
Executive Reporting Platform."""
from __future__ import annotations

import enum


# -- data warehouse / metrics registry -------------------------------------------------------------

class DataSourceType(str, enum.Enum):
    AUTHENTICATION = "authentication"
    ORGANIZATIONS = "organizations"
    USERS = "users"
    AGENTS = "agents"
    WORKFLOWS = "workflows"
    PROMPTS = "prompts"
    MODELS = "models"
    MEMORY = "memory"
    KNOWLEDGE = "knowledge"
    TOOLS = "tools"
    API_GATEWAY = "api_gateway"
    INFRASTRUCTURE = "infrastructure"
    SECURITY = "security"
    MONITORING = "monitoring"
    DEPLOYMENTS = "deployments"
    DEVELOPER_PLATFORM = "developer_platform"


class MetricUnit(str, enum.Enum):
    COUNT = "count"
    SECONDS = "seconds"
    MILLISECONDS = "milliseconds"
    BYTES = "bytes"
    CURRENCY_USD = "currency_usd"
    PERCENTAGE = "percentage"
    RATIO = "ratio"
    TOKENS = "tokens"


class MetricAggregationType(str, enum.Enum):
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    P50 = "p50"
    P95 = "p95"
    P99 = "p99"


# -- analytics / aggregation engine -----------------------------------------------------------------

class AnalyticsDomain(str, enum.Enum):
    BUSINESS = "business"
    AI = "ai"
    FINANCIAL = "financial"
    PERFORMANCE = "performance"


class RollupPeriod(str, enum.Enum):
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


# -- KPI engine ---------------------------------------------------------------------------------------

class KpiScope(str, enum.Enum):
    CUSTOM = "custom"
    ORGANIZATION = "organization"
    WORKSPACE = "workspace"
    ENGINEERING = "engineering"
    AI = "ai"
    BUSINESS = "business"
    EXECUTIVE = "executive"


class KpiStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class KpiHealth(str, enum.Enum):
    ON_TARGET = "on_target"
    AT_RISK = "at_risk"
    BREACHED = "breached"


# -- reporting platform ---------------------------------------------------------------------------------

class ReportType(str, enum.Enum):
    EXECUTIVE = "executive"
    ENGINEERING = "engineering"
    AI_PERFORMANCE = "ai_performance"
    SECURITY = "security"
    FINANCIAL = "financial"
    COMPLIANCE = "compliance"
    OPERATIONAL = "operational"
    USAGE = "usage"
    CUSTOM = "custom"


class ReportFormat(str, enum.Enum):
    JSON = "json"
    PDF = "pdf"
    CSV = "csv"
    HTML = "html"


class ReportSchedule(str, enum.Enum):
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class ReportDefinitionStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class ReportRunStatus(str, enum.Enum):
    QUEUED = "queued"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


# -- forecasting engine ---------------------------------------------------------------------------------

class ForecastType(str, enum.Enum):
    USAGE = "usage"
    COST = "cost"
    CAPACITY = "capacity"
    GROWTH = "growth"
    RESOURCE = "resource"
    PERFORMANCE_TREND = "performance_trend"
    ANOMALY = "anomaly"
    RISK = "risk"


class ForecastMethod(str, enum.Enum):
    MOVING_AVERAGE = "moving_average"
    LINEAR_REGRESSION = "linear_regression"
    EXPONENTIAL_SMOOTHING = "exponential_smoothing"


class ForecastJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# -- recommendation engine ---------------------------------------------------------------------------------

class RecommendationCategory(str, enum.Enum):
    INFRASTRUCTURE_OPTIMIZATION = "infrastructure_optimization"
    COST_OPTIMIZATION = "cost_optimization"
    PROMPT_OPTIMIZATION = "prompt_optimization"
    WORKFLOW_OPTIMIZATION = "workflow_optimization"
    AGENT_OPTIMIZATION = "agent_optimization"
    RESOURCE_ALLOCATION = "resource_allocation"
    CAPACITY_PLANNING = "capacity_planning"
    SECURITY_IMPROVEMENT = "security_improvement"


class RecommendationImpact(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecommendationStatus(str, enum.Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    IMPLEMENTED = "implemented"


# -- visualization / dashboard platform ---------------------------------------------------------------------

class VisualizationType(str, enum.Enum):
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    HEATMAP = "heatmap"
    TIMELINE = "timeline"
    TREND_CHART = "trend_chart"
    NETWORK_GRAPH = "network_graph"
    TREE_MAP = "tree_map"
    GEO_MAP = "geo_map"
    SCORECARD = "scorecard"
    TABLE = "table"
    CUSTOM_WIDGET = "custom_widget"


class DashboardStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class DashboardVisibility(str, enum.Enum):
    PRIVATE = "private"
    TEAM = "team"
    ORGANIZATION = "organization"
    PUBLIC = "public"


# -- security / governance ---------------------------------------------------------------------------------

class SecurityRoleLevel(str, enum.Enum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    EDITOR = "editor"
    ADMIN = "admin"


class RowLevelSecurityMode(str, enum.Enum):
    TENANT_SCOPED = "tenant_scoped"
    WORKSPACE_SCOPED = "workspace_scoped"
    UNRESTRICTED = "unrestricted"


class AuditActionType(str, enum.Enum):
    VIEW = "view"
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    EXPORT = "export"
    SHARE = "share"


class DataLineageStageType(str, enum.Enum):
    SOURCE = "source"
    TRANSFORM = "transform"
    AGGREGATE = "aggregate"
    OUTPUT = "output"


# -- observability ---------------------------------------------------------------------------------------

class UsageEventType(str, enum.Enum):
    DASHBOARD_VIEW = "dashboard_view"
    REPORT_GENERATE = "report_generate"
    QUERY_EXECUTE = "query_execute"
    VISUALIZATION_RENDER = "visualization_render"
    FORECAST_RUN = "forecast_run"
    RECOMMENDATION_ACTION = "recommendation_action"


class RecommendationOutcome(str, enum.Enum):
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    IMPLEMENTED = "implemented"


# -- exports ---------------------------------------------------------------------------------------------

class ExportFormat(str, enum.Enum):
    CSV = "csv"
    JSON = "json"
    XLSX = "xlsx"
    PDF = "pdf"


class ExportJobStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
