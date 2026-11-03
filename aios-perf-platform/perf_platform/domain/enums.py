"""Enumerations shared across the domain, ORM, and service layers."""
from __future__ import annotations

from enum import Enum


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RecommendationStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    APPLIED = "applied"
    REJECTED = "rejected"
    EXPIRED = "expired"


class CacheLayer(str, Enum):
    MEMORY = "memory"
    REDIS = "redis"
    DISK = "disk"
    CDN = "cdn"
    PROMPT = "prompt"
    EMBEDDING = "embedding"
    RESPONSE = "response"
    WORKFLOW = "workflow"
    MODEL = "model"
    FEATURE = "feature"
    API = "api"


class ModelTier(str, Enum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"
    REASONING = "reasoning"
    VISION = "vision"
    CODE = "code"


class TaskComplexity(str, Enum):
    TRIVIAL = "trivial"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    EXPERT = "expert"


class UserTier(str, Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"


class CostCategory(str, Enum):
    TOKEN = "token"
    GPU = "gpu"
    CPU = "cpu"
    MEMORY = "memory"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"
    INFRASTRUCTURE = "infrastructure"


class CostEntityType(str, Enum):
    USER = "user"
    ORGANIZATION = "organization"
    WORKFLOW = "workflow"
    AGENT = "agent"
    MODEL = "model"


class RecommendationCategory(str, Enum):
    PROMPT = "prompt"
    DATABASE = "database"
    WORKFLOW = "workflow"
    CACHING = "caching"
    MODEL_DOWNGRADE = "model_downgrade"
    INFRASTRUCTURE = "infrastructure"
    SCALING = "scaling"


class GpuPoolType(str, Enum):
    SHARED = "shared"
    DEDICATED = "dedicated"
    SPOT = "spot"
    RESERVED = "reserved"
