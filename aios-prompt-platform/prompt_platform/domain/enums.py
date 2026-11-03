"""All status/type enums for the Prompt Engineering Platform domain."""
from __future__ import annotations

from enum import Enum


class PromptStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class PromptVisibility(str, Enum):
    PRIVATE = "private"
    ORGANIZATION = "organization"
    PUBLIC = "public"


class VersionStatus(str, Enum):
    # Pure approval-workflow status, orthogonal to VersionBranch (the
    # deployment lane). A version can be APPROVED and sitting on the
    # EXPERIMENTAL branch, or APPROVED and promoted to the PRODUCTION
    # branch; status answers "has this been reviewed," branch answers
    # "where does it run."
    DRAFT = "draft"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class VersionBranch(str, Enum):
    EXPERIMENTAL = "experimental"
    STABLE = "stable"
    PRODUCTION = "production"


class DependencyRelationship(str, Enum):
    COMPOSITION = "composition"
    REFERENCE = "reference"
    CHAIN = "chain"


class TestRunType(str, Enum):
    SINGLE = "single"
    BATCH = "batch"
    REGRESSION = "regression"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AssertionType(str, Enum):
    EXACT = "exact"
    CONTAINS = "contains"
    REGEX = "regex"
    JSON_SCHEMA = "json_schema"
    NOT_CONTAINS = "not_contains"


class EvalType(str, Enum):
    AUTOMATIC = "automatic"
    HUMAN = "human"
    PAIRWISE = "pairwise"
    BENCHMARK = "benchmark"


class EvalMetric(str, Enum):
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    CONSISTENCY = "consistency"
    GROUNDEDNESS = "groundedness"
    FAITHFULNESS = "faithfulness"
    SAFETY = "safety"
    FORMATTING = "formatting"
    LATENCY = "latency"
    TOKEN_USAGE = "token_usage"
    COST = "cost"
    USER_RATING = "user_rating"


class ExperimentStatus(str, Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class DeploymentEnvironment(str, Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class DeploymentStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    DEPLOYED = "deployed"
    ROLLED_BACK = "rolled_back"
    REJECTED = "rejected"


class OptimizationObjective(str, Enum):
    QUALITY = "quality"
    COST = "cost"
    LATENCY = "latency"
    TOKEN_COUNT = "token_count"


class OptimizationCategory(str, Enum):
    INSTRUCTION_CLARITY = "instruction_clarity"
    FEW_SHOT_EXAMPLES = "few_shot_examples"
    COMPRESSION = "compression"
    EXPANSION = "expansion"
    VARIABLE_USAGE = "variable_usage"
    RESPONSE_FORMATTING = "response_formatting"
    COST_LATENCY = "cost_latency"


class Role(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class Permission(str, Enum):
    PROMPT_READ = "prompt:read"
    PROMPT_WRITE = "prompt:write"
    PROMPT_DELETE = "prompt:delete"
    VERSION_CREATE = "version:create"
    VERSION_APPROVE = "version:approve"
    VERSION_PROMOTE = "version:promote"
    TEST_RUN = "test:run"
    EVAL_RUN = "eval:run"
    OPTIMIZE_RUN = "optimize:run"
    EXPERIMENT_RUN = "experiment:run"
    DEPLOYMENT_REQUEST = "deployment:request"
    DEPLOYMENT_APPROVE = "deployment:approve"
    DEPLOYMENT_ROLLBACK = "deployment:rollback"
    AUDIT_READ = "audit:read"
    WORKSPACE_MANAGE = "workspace:manage"


ROLE_PERMISSIONS: dict[Role, frozenset[Permission]] = {
    Role.OWNER: frozenset(Permission),
    Role.ADMIN: frozenset(
        p for p in Permission if p != Permission.WORKSPACE_MANAGE
    ) | frozenset({Permission.WORKSPACE_MANAGE}),
    Role.EDITOR: frozenset(
        {
            Permission.PROMPT_READ, Permission.PROMPT_WRITE, Permission.VERSION_CREATE,
            Permission.TEST_RUN, Permission.EVAL_RUN, Permission.OPTIMIZE_RUN,
            Permission.EXPERIMENT_RUN, Permission.DEPLOYMENT_REQUEST,
        }
    ),
    Role.REVIEWER: frozenset(
        {Permission.PROMPT_READ, Permission.VERSION_APPROVE, Permission.DEPLOYMENT_APPROVE, Permission.AUDIT_READ}
    ),
    Role.VIEWER: frozenset({Permission.PROMPT_READ}),
}


def permissions_for_role(role: Role) -> frozenset[Permission]:
    return ROLE_PERMISSIONS.get(role, frozenset())
