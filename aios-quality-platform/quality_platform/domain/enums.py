"""Enum catalog for the Enterprise Testing, Quality Engineering &
Reliability Platform."""
from __future__ import annotations

import enum


# -- common ---------------------------------------------------------------------------------------

class JobStatus(str, enum.Enum):
    """Shared guarded lifecycle for every job/run-style resource in
    this platform (test runs, chaos experiments, performance runs,
    regression scans, certification runs): queued -> running ->
    completed/failed. Reused across modules rather than re-declared
    per module, since the transition semantics are identical."""
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


# -- test management & automation (test pyramid) ---------------------------------------------------

class TestType(str, enum.Enum):
    UNIT = "unit"
    COMPONENT = "component"
    INTEGRATION = "integration"
    CONTRACT = "contract"
    API = "api"
    DATABASE = "database"
    UI = "ui"
    WORKFLOW = "workflow"
    AGENT = "agent"
    PROMPT = "prompt"
    MEMORY = "memory"
    TOOL = "tool"
    SYSTEM = "system"
    E2E = "e2e"
    ACCEPTANCE = "acceptance"


class TestSuiteStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class TestCaseResultStatus(str, enum.Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    FLAKY = "flaky"
    ERROR = "error"


# -- AI quality / evaluation regression engine -------------------------------------------------------

class AiQualityDimension(str, enum.Enum):
    PROMPT_ACCURACY = "prompt_accuracy"
    REASONING_QUALITY = "reasoning_quality"
    PLANNING_QUALITY = "planning_quality"
    MEMORY_RETRIEVAL = "memory_retrieval"
    TOOL_SELECTION = "tool_selection"
    WORKFLOW_EXECUTION = "workflow_execution"
    AGENT_COLLABORATION = "agent_collaboration"
    GROUNDEDNESS = "groundedness"
    HALLUCINATION_RATE = "hallucination_rate"
    CITATION_QUALITY = "citation_quality"
    INSTRUCTION_FOLLOWING = "instruction_following"
    CONSISTENCY = "consistency"
    STRUCTURED_OUTPUT = "structured_output"


class RegressionSeverity(str, enum.Enum):
    NONE = "none"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


# -- performance testing engine ------------------------------------------------------------------------

class PerformanceTestType(str, enum.Enum):
    LOAD = "load"
    STRESS = "stress"
    SPIKE = "spike"
    SOAK = "soak"
    SCALABILITY = "scalability"
    CONCURRENCY = "concurrency"


class BenchmarkMetricType(str, enum.Enum):
    LATENCY_P50 = "latency_p50"
    LATENCY_P95 = "latency_p95"
    LATENCY_P99 = "latency_p99"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    CPU_UTILIZATION = "cpu_utilization"
    MEMORY_UTILIZATION = "memory_utilization"


# -- chaos engineering platform -------------------------------------------------------------------------

class ChaosFailureType(str, enum.Enum):
    NODE_FAILURE = "node_failure"
    DATABASE_FAILURE = "database_failure"
    NETWORK_LATENCY = "network_latency"
    PACKET_LOSS = "packet_loss"
    SERVICE_SHUTDOWN = "service_shutdown"
    WORKER_FAILURE = "worker_failure"
    QUEUE_FAILURE = "queue_failure"
    CACHE_FAILURE = "cache_failure"
    STORAGE_FAILURE = "storage_failure"
    GPU_FAILURE = "gpu_failure"
    EXTERNAL_API_FAILURE = "external_api_failure"
    REGION_FAILURE = "region_failure"


# -- security testing engine -----------------------------------------------------------------------------

class SecurityTestType(str, enum.Enum):
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RBAC = "rbac"
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    SECRETS = "secrets"
    API_SECURITY = "api_security"
    DEPENDENCY_SCAN = "dependency_scan"
    CONTAINER_SECURITY = "container_security"
    INFRASTRUCTURE_SECURITY = "infrastructure_security"
    COMPLIANCE = "compliance"


class SecurityFindingSeverity(str, enum.Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# -- API & workflow validation -----------------------------------------------------------------------------

class ApiValidationType(str, enum.Enum):
    SCHEMA = "schema"
    REQUEST = "request"
    RESPONSE = "response"
    CONTRACT = "contract"
    BACKWARD_COMPATIBILITY = "backward_compatibility"
    VERSION_COMPATIBILITY = "version_compatibility"
    SDK_COMPATIBILITY = "sdk_compatibility"


class ValidationOutcome(str, enum.Enum):
    PASSED = "passed"
    FAILED = "failed"


class WorkflowValidationCheck(str, enum.Enum):
    LOGIC = "logic"
    NODE_EXECUTION = "node_execution"
    PARALLEL_EXECUTION = "parallel_execution"
    RETRIES = "retries"
    COMPENSATION = "compensation"
    TIMEOUT_HANDLING = "timeout_handling"
    FAILURE_RECOVERY = "failure_recovery"
    APPROVAL_CHAINS = "approval_chains"
    HUMAN_IN_THE_LOOP = "human_in_the_loop"


# -- reliability engineering --------------------------------------------------------------------------------

class ReliabilityMetricType(str, enum.Enum):
    AVAILABILITY = "availability"
    RELIABILITY = "reliability"
    DURABILITY = "durability"
    ERROR_BUDGET = "error_budget"
    MTTD = "mttd"
    MTTR = "mttr"
    MTBF = "mtbf"
    RECOVERY_SUCCESS_RATE = "recovery_success_rate"


class SloStatus(str, enum.Enum):
    MEETING = "meeting"
    AT_RISK = "at_risk"
    BREACHED = "breached"


# -- quality gates & coverage platform --------------------------------------------------------------------------

class QualityGateCheckType(str, enum.Enum):
    TEST_COVERAGE = "test_coverage"
    SECURITY = "security"
    REGRESSION = "regression"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    API_COMPATIBILITY = "api_compatibility"
    DOCUMENTATION = "documentation"
    QUALITY_SCORE = "quality_score"


class QualityGateStatus(str, enum.Enum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    WAIVED = "waived"


class CoverageType(str, enum.Enum):
    CODE = "code"
    API = "api"
    WORKFLOW = "workflow"
    PROMPT = "prompt"
    AGENT = "agent"
    MODEL = "model"
    DATASET = "dataset"
    UI = "ui"
    INTEGRATION = "integration"


# -- failure analysis & risk analysis -------------------------------------------------------------------------------

class FailurePatternType(str, enum.Enum):
    REGRESSION = "regression"
    ROOT_CAUSE = "root_cause"
    FLAKY_TEST = "flaky_test"
    PERFORMANCE_REGRESSION = "performance_regression"
    MEMORY_LEAK = "memory_leak"
    CONCURRENCY_ISSUE = "concurrency_issue"
    INFRASTRUCTURE_ISSUE = "infrastructure_issue"


class RiskLevel(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# -- release certification engine -----------------------------------------------------------------------------------

class CertificationDecision(str, enum.Enum):
    APPROVED = "approved"
    APPROVED_WITH_CONDITIONS = "approved_with_conditions"
    REJECTED = "rejected"


# -- observability --------------------------------------------------------------------------------------------------

class TrendMetricType(str, enum.Enum):
    TEST_EXECUTIONS = "test_executions"
    QUALITY = "quality"
    REGRESSION = "regression"
    COVERAGE = "coverage"
    FAILURE = "failure"
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    RELEASE = "release"
