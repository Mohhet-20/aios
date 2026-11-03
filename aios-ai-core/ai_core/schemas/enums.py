"""Shared enums used across the AI Core. Kept dependency-free (no imports
from other ai_core modules) so every other package can import from here
without risking circular imports.
"""
from __future__ import annotations

from enum import Enum


class ProviderName(str, Enum):
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    VLLM = "vllm"
    LMSTUDIO = "lmstudio"
    LOCAL_TRANSFORMERS = "local_transformers"


class Role(str, Enum):
    SYSTEM = "system"
    DEVELOPER = "developer"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ContentType(str, Enum):
    TEXT = "text"
    IMAGE_URL = "image_url"
    IMAGE_BASE64 = "image_base64"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"


class Capability(str, Enum):
    """Flags tracked per model in the registry and used by the router for
    capability-based routing decisions."""

    STREAMING = "streaming"
    VISION = "vision"
    AUDIO_INPUT = "audio_input"
    AUDIO_OUTPUT = "audio_output"
    TOOL_CALLING = "tool_calling"
    JSON_OUTPUT = "json_output"
    EMBEDDING = "embedding"
    REASONING = "reasoning"


class ModelStatus(str, Enum):
    AVAILABLE = "available"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"
    DEPRECATED = "deprecated"


class FinishReason(str, Enum):
    STOP = "stop"
    LENGTH = "length"
    TOOL_CALLS = "tool_calls"
    CONTENT_FILTER = "content_filter"
    ERROR = "error"
    CANCELLED = "cancelled"


class ToolSideEffect(str, Enum):
    NONE = "none"
    READ = "read"
    WRITE = "write"
    EXTERNAL = "external"


class RoutingStrategyName(str, Enum):
    TASK_BASED = "task_based"
    CAPABILITY = "capability"
    COST_AWARE = "cost_aware"
    LATENCY_AWARE = "latency_aware"
    PRIORITY = "priority"
    REGIONAL = "regional"
    LOAD_BALANCING = "load_balancing"
    CANARY = "canary"
    AB_TEST = "ab_test"
    RULE_BASED = "rule_based"
    ML_BASED = "ml_based"  # future seam — see router/strategies.py docstring
