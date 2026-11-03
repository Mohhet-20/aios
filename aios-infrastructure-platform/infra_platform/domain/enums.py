"""Enumerations shared across the domain, ORM, and service layers."""
from __future__ import annotations

import enum


class ServiceType(str, enum.Enum):
    API = "api"
    WORKER = "worker"
    BACKGROUND_JOB = "background_job"
    SCHEDULER = "scheduler"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    VECTOR_DB = "vector_db"
    MODEL_SERVER = "model_server"
    INFERENCE_SERVICE = "inference_service"
    STORAGE = "storage"
    CDN = "cdn"
    GATEWAY = "gateway"
    LOAD_BALANCER = "load_balancer"
    EDGE_NODE = "edge_node"
    GPU_WORKER = "gpu_worker"
    CPU_WORKER = "cpu_worker"


class ServiceStatus(str, enum.Enum):
    PROVISIONING = "provisioning"
    RUNNING = "running"
    DEGRADED = "degraded"
    STOPPED = "stopped"
    TERMINATED = "terminated"


class ImageStatus(str, enum.Enum):
    BUILDING = "building"
    SCANNING = "scanning"
    SCAN_FAILED = "scan_failed"
    SIGNED = "signed"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    QUARANTINED = "quarantined"


class ScanSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return {"low": 0, "medium": 1, "high": 2, "critical": 3}[self.value]


class ClusterStatus(str, enum.Enum):
    PROVISIONING = "provisioning"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DECOMMISSIONED = "decommissioned"


class NodePoolType(str, enum.Enum):
    CPU = "cpu"
    GPU = "gpu"


class K8sResourceKind(str, enum.Enum):
    DEPLOYMENT = "deployment"
    STATEFULSET = "statefulset"
    DAEMONSET = "daemonset"
    JOB = "job"
    CRONJOB = "cronjob"
    SERVICE = "service"
    INGRESS = "ingress"
    CONFIGMAP = "configmap"
    SECRET = "secret"
    PERSISTENT_VOLUME = "persistent_volume"


class AutoscalerKind(str, enum.Enum):
    HPA = "hpa"
    VPA = "vpa"


class PipelineStageType(str, enum.Enum):
    BUILD = "build"
    TEST = "test"
    STATIC_ANALYSIS = "static_analysis"
    SECURITY_SCAN = "security_scan"
    PUBLISH = "publish"
    DEPLOY = "deploy"


class PipelineRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GateStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    BYPASSED = "bypassed"


class ReleaseStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    RELEASED = "released"
    ROLLED_BACK = "rolled_back"


class ModelStage(str, enum.Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"

    @property
    def rank(self) -> int:
        return {"development": 0, "staging": 1, "production": 2, "archived": 3}[self.value]


class ModelApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RunStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


class FeatureValueType(str, enum.Enum):
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    BOOL = "bool"
    VECTOR = "vector"
    TIMESTAMP = "timestamp"


class FeatureStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class ArtifactType(str, enum.Enum):
    MODEL = "model"
    DATASET = "dataset"
    EMBEDDING = "embedding"
    PROMPT_TEMPLATE = "prompt_template"
    AGENT_CONFIG = "agent_config"
    WORKFLOW_TEMPLATE = "workflow_template"
    EVALUATION_REPORT = "evaluation_report"
    TRAINING_OUTPUT = "training_output"
    DEPLOYMENT_PACKAGE = "deployment_package"


class InferenceMode(str, enum.Enum):
    REAL_TIME = "real_time"
    BATCH = "batch"
    STREAMING = "streaming"
    ASYNC = "async"


class ComputeType(str, enum.Enum):
    CPU = "cpu"
    GPU = "gpu"


class DeploymentStrategy(str, enum.Enum):
    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    SHADOW = "shadow"
    RECREATE = "recreate"


class DeploymentStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    PAUSED = "paused"


class ScalingPolicyType(str, enum.Enum):
    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    CLUSTER = "cluster"
    GPU = "gpu"
    QUEUE_BASED = "queue_based"
    PREDICTIVE = "predictive"
    COST_AWARE = "cost_aware"


class ScalingDirection(str, enum.Enum):
    UP = "up"
    DOWN = "down"


class CloudProvider(str, enum.Enum):
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    ON_PREM = "on_prem"
    HYBRID = "hybrid"
    EDGE = "edge"


class BackupStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class RecoveryStatus(str, enum.Enum):
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class FailoverStatus(str, enum.Enum):
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class InfraRole(str, enum.Enum):
    """Ordered — deliberately smaller than the Identity Platform's
    fine-grained resource_type:action grammar, matching the precedent
    set by the Observability and Security Platforms' own RBAC."""
    VIEWER = "viewer"
    OPERATOR = "operator"
    ADMIN = "admin"

    @property
    def rank(self) -> int:
        return {"viewer": 0, "operator": 1, "admin": 2}[self.value]
