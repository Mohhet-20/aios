"""Provider-agnostic response contracts returned by the execution engine —
never a raw provider SDK response."""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from ai_core.schemas.enums import FinishReason
from ai_core.schemas.tools import ToolCall
from ai_core.schemas.usage import CostBreakdown, TokenUsage


class ExecutionMetadata(BaseModel):
    """Everything about *how* a request was executed, independent of the
    content of the response. This is what observability/cost/monitoring
    consume — it's attached to every GenerationResponse."""

    request_id: str
    provider: str
    model: str
    attempted_models: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    retries: int = 0
    fallback_used: bool = False
    cache_hit: bool = False
    cancelled: bool = False


class GenerationResponse(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex)
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    finish_reason: FinishReason = FinishReason.STOP
    usage: TokenUsage = Field(default_factory=TokenUsage)
    cost: CostBreakdown = Field(default_factory=CostBreakdown)
    execution: ExecutionMetadata
    structured_output: dict[str, Any] | None = None
    confidence: float | None = None
    raw_provider_response: dict[str, Any] | None = Field(
        default=None, description="Only populated when settings.debug_include_raw_response is true."
    )


class StreamChunk(BaseModel):
    request_id: str
    delta: str = ""
    tool_call_delta: dict[str, Any] | None = None
    finish_reason: FinishReason | None = None
    usage: TokenUsage | None = Field(default=None, description="Populated only on the final chunk.")
    is_final: bool = False


class EmbeddingResponse(BaseModel):
    request_id: str
    embeddings: list[list[float]]
    model: str
    provider: str
    dimensions: int
    usage: TokenUsage = Field(default_factory=TokenUsage)
    cached: list[bool] = Field(default_factory=list)
    version: str = "v1"
