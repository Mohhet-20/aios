"""Domain enums shared between pure-Python entities and ORM models.
Grouped by module, mirroring release_platform's folder layout."""
from __future__ import annotations

import enum


# -- shared job lifecycle (deployments, update jobs) -----------------------------------------------------

class JobStatus(str, enum.Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


# -- release & version management -------------------------------------------------------------------------

class ReleaseStatus(str, enum.Enum):
    DRAFT = "draft"
    CANDIDATE = "candidate"
    APPROVED = "approved"
    RELEASED = "released"
    DEPRECATED = "deprecated"
    YANKED = "yanked"


class ReleaseChannel(str, enum.Enum):
    DEV = "dev"
    ALPHA = "alpha"
    BETA = "beta"
    RC = "rc"
    STABLE = "stable"
    LTS = "lts"
    HOTFIX = "hotfix"
    PATCH = "patch"


# -- artifact management & enterprise distribution ---------------------------------------------------------

class ArtifactType(str, enum.Enum):
    BACKEND_PACKAGE = "backend_package"
    FRONTEND_PACKAGE = "frontend_package"
    SDK_PACKAGE = "sdk_package"
    CLI_PACKAGE = "cli_package"
    DOCKER_IMAGE = "docker_image"
    KUBERNETES_MANIFEST = "kubernetes_manifest"
    HELM_CHART = "helm_chart"
    TERRAFORM_MODULE = "terraform_module"
    WORKFLOW_TEMPLATE = "workflow_template"
    AGENT_TEMPLATE = "agent_template"
    PROMPT_TEMPLATE = "prompt_template"


class DistributionChannelType(str, enum.Enum):
    DOCKER_REGISTRY = "docker_registry"
    CONTAINER_REGISTRY = "container_registry"
    HELM_REPOSITORY = "helm_repository"
    PACKAGE_REGISTRY = "package_registry"
    PRIVATE_ENTERPRISE = "private_enterprise"
    OFFLINE_BUNDLE = "offline_bundle"


# -- deployment orchestration ------------------------------------------------------------------------------

class DeploymentTarget(str, enum.Enum):
    CLOUD = "cloud"
    ON_PREM = "on_prem"
    HYBRID = "hybrid"
    EDGE = "edge"
    MULTI_REGION = "multi_region"
    MULTI_CLUSTER = "multi_cluster"
    MULTI_TENANT = "multi_tenant"
    AIR_GAPPED = "air_gapped"
    OFFLINE = "offline"


# -- rollout engine -----------------------------------------------------------------------------------------

class RolloutStrategy(str, enum.Enum):
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    ROLLING = "rolling"
    SHADOW = "shadow"
    PROGRESSIVE = "progressive"
    PERCENTAGE = "percentage"
    REGION = "region"
    ORGANIZATION = "organization"
    TENANT = "tenant"
    FEATURE = "feature"


class RolloutStatus(str, enum.Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABORTED = "aborted"


# -- feature flag platform ------------------------------------------------------------------------------------

class FeatureFlagScope(str, enum.Enum):
    GLOBAL = "global"
    ORGANIZATION = "organization"
    WORKSPACE = "workspace"
    USER = "user"
    EXPERIMENT = "experiment"


# -- update infrastructure ------------------------------------------------------------------------------------

class UpdateType(str, enum.Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    SCHEDULED = "scheduled"
    DELTA = "delta"
    PATCH = "patch"
    OFFLINE = "offline"
    ROLLBACK = "rollback"


# -- license management ------------------------------------------------------------------------------------------

class LicenseType(str, enum.Enum):
    ENTERPRISE = "enterprise"
    ORGANIZATION = "organization"
    TRIAL = "trial"
    FEATURE = "feature"
    SEAT_BASED = "seat_based"


class LicenseStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    TRIAL = "trial"


# -- environment management ------------------------------------------------------------------------------------------

class EnvironmentType(str, enum.Enum):
    DEVELOPMENT = "development"
    TESTING = "testing"
    QA = "qa"
    STAGING = "staging"
    PRODUCTION = "production"
    SANDBOX = "sandbox"
    CUSTOMER_PREVIEW = "customer_preview"
    ENTERPRISE_DEDICATED = "enterprise_dedicated"


# -- deployment validation ----------------------------------------------------------------------------------------

class HealthCheckTarget(str, enum.Enum):
    APPLICATION = "application"
    API = "api"
    DATABASE = "database"
    WORKFLOW = "workflow"
    AI_SERVICES = "ai_services"
    AGENT_SERVICES = "agent_services"
    MEMORY_SERVICES = "memory_services"
    SECURITY_PLATFORM = "security_platform"
    MONITORING_PLATFORM = "monitoring_platform"
    ANALYTICS_PLATFORM = "analytics_platform"


class HealthCheckStatus(str, enum.Enum):
    PASSED = "passed"
    FAILED = "failed"
    DEGRADED = "degraded"


# -- rollback engine -----------------------------------------------------------------------------------------

class RollbackType(str, enum.Enum):
    AUTOMATIC = "automatic"
    MANUAL = "manual"
    PARTIAL = "partial"
    DATABASE = "database"
    CONFIGURATION = "configuration"
    FEATURE = "feature"
    MODEL = "model"
    INFRASTRUCTURE = "infrastructure"


# -- security & supply chain -----------------------------------------------------------------------------------------

class ApprovalDecision(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
