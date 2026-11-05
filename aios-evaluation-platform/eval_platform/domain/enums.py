"""Every enum the evaluation/benchmarking/observability domain needs.
Grouped by evaluation category."""
from __future__ import annotations

from enum import Enum


# -- evaluation types (spec: "EVALUATION TYPES") -----------------------------------

class EvaluationCategory(str, Enum):
    PROMPT = "prompt"
    AGENT = "agent"
    WORKFLOW = "workflow"
    TOOL = "tool"
    MEMORY_RETRIEVAL = "memory_retrieval"
    KNOWLEDGE_QUALITY = "knowledge_quality"
    LLM = "llm"
    REASONING = "reasoning"
    PLANNING = "planning"
    TASK_COMPLETION = "task_completion"
    CONVERSATION = "conversation"
    SAFETY = "safety"
    GROUNDEDNESS = "groundedness"
    STRUCTURED_OUTPUT = "structured_output"
    API_RESPONSE = "api_response"
    END_TO_END_SYSTEM = "end_to_end_system"


class EvaluationStatus(str, Enum):
    """Lifecycle of the Evaluation *definition* (identity), not a run."""
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class EvaluationVersionStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"


class RunStatus(str, Enum):
    """Shared by EvaluationRun and BenchmarkRun — identical shape to
    ToolExecution's status machine in the Tool Platform."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"

    @classmethod
    def terminal(cls) -> frozenset["RunStatus"]:
        return frozenset({cls.SUCCEEDED, cls.FAILED, cls.TIMED_OUT, cls.CANCELLED})


# -- datasets (spec: "BENCHMARK DATASETS") -----------------------------------------

class DatasetType(str, Enum):
    GOLDEN = "golden"
    SYNTHETIC = "synthetic"
    HUMAN_ANNOTATED = "human_annotated"
    REGRESSION = "regression"
    PRODUCTION_SAMPLE = "production_sample"
    EVALUATION_SUITE = "evaluation_suite"


class DatasetStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


# -- metrics (spec: "QUALITY METRICS") ---------------------------------------------

class MetricCategory(str, Enum):
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1_SCORE = "f1_score"
    TASK_SUCCESS_RATE = "task_success_rate"
    REASONING_QUALITY = "reasoning_quality"
    PLANNING_QUALITY = "planning_quality"
    GROUNDEDNESS = "groundedness"
    FAITHFULNESS = "faithfulness"
    HALLUCINATION_RATE = "hallucination_rate"
    CITATION_QUALITY = "citation_quality"
    RESPONSE_COMPLETENESS = "response_completeness"
    INSTRUCTION_FOLLOWING = "instruction_following"
    CONSISTENCY = "consistency"
    FORMATTING_COMPLIANCE = "formatting_compliance"
    JSON_VALIDATION = "json_validation"
    LATENCY = "latency"
    TOKEN_USAGE = "token_usage"
    COST = "cost"
    RELIABILITY = "reliability"


class MetricValueType(str, Enum):
    NUMERIC = "numeric"
    BOOLEAN = "boolean"
    CATEGORICAL = "categorical"


# -- benchmarking (spec: "MODEL BENCHMARKING" / "PROMPT BENCHMARKING") ------------

class BenchmarkType(str, Enum):
    MODEL = "model"
    PROMPT = "prompt"
    AGENT = "agent"
    WORKFLOW = "workflow"


class BenchmarkMode(str, Enum):
    """How candidates in a benchmark run are compared."""
    SINGLE = "single"
    AB_TEST = "ab_test"
    MULTIVARIATE = "multivariate"
    REGRESSION = "regression"


# -- observability (spec: "OBSERVABILITY PLATFORM") --------------------------------

class ObservabilityEventType(str, Enum):
    PROMPT_EXECUTION = "prompt_execution"
    AGENT_EXECUTION = "agent_execution"
    WORKFLOW_EXECUTION = "workflow_execution"
    TOOL_CALL = "tool_call"
    MEMORY_RETRIEVAL = "memory_retrieval"
    MODEL_USAGE = "model_usage"


class ObservabilityEventStatus(str, Enum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    RETRIED = "retried"


# -- alerting (spec: "ALERTING") ---------------------------------------------------

class AlertCategory(str, Enum):
    PERFORMANCE = "performance"
    FAILURE = "failure"
    QUALITY = "quality"
    SAFETY = "safety"
    COST = "cost"
    LATENCY = "latency"
    REGRESSION = "regression"
    AVAILABILITY = "availability"
    CUSTOM = "custom"


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertStatus(str, Enum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class AlertComparator(str, Enum):
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    NEQ = "neq"


# -- analytics / improvement loop (spec: "ANALYTICS" / "AI IMPROVEMENT LOOP") -----

class AnalyticsSnapshotType(str, Enum):
    TREND = "trend"
    QUALITY = "quality"
    RELIABILITY = "reliability"
    COST = "cost"
    USAGE = "usage"
    REGRESSION = "regression"


class RecommendationCategory(str, Enum):
    PROMPT_IMPROVEMENT = "prompt_improvement"
    AGENT_OPTIMIZATION = "agent_optimization"
    WORKFLOW_OPTIMIZATION = "workflow_optimization"
    DATASET_GAP = "dataset_gap"
    COST_OPTIMIZATION = "cost_optimization"
    RELIABILITY = "reliability"


class RecommendationStatus(str, Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"


# -- governance (spec: "SECURITY & GOVERNANCE") ------------------------------------

class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class Permission(str, Enum):
    EVALUATION_READ = "evaluation:read"
    EVALUATION_WRITE = "evaluation:write"
    EVALUATION_EXECUTE = "evaluation:execute"
    DATASET_READ = "dataset:read"
    DATASET_WRITE = "dataset:write"
    BENCHMARK_EXECUTE = "benchmark:execute"
    ALERT_MANAGE = "alert:manage"
    REPORT_READ = "report:read"
    GOVERNANCE_ADMIN = "governance:admin"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.VIEWER: frozenset({Permission.EVALUATION_READ, Permission.DATASET_READ, Permission.REPORT_READ}),
    Role.ANALYST: frozenset({
        Permission.EVALUATION_READ, Permission.EVALUATION_WRITE, Permission.EVALUATION_EXECUTE,
        Permission.DATASET_READ, Permission.DATASET_WRITE, Permission.BENCHMARK_EXECUTE, Permission.REPORT_READ,
    }),
    Role.ADMIN: frozenset({
        Permission.EVALUATION_READ, Permission.EVALUATION_WRITE, Permission.EVALUATION_EXECUTE,
        Permission.DATASET_READ, Permission.DATASET_WRITE, Permission.BENCHMARK_EXECUTE,
        Permission.ALERT_MANAGE, Permission.REPORT_READ,
    }),
    Role.OWNER: frozenset(Permission),
}


def permissions_for_role(role: Role | str) -> frozenset[Permission]:
    return ROLE_PERMISSIONS[Role(role)]


class Priority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
