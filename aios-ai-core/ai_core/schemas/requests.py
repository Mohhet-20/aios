"""Provider-agnostic request contracts. Everything a caller (a business
service, the gateway, or a test) constructs to ask the AI Core for
something goes through one of these — never a provider SDK's own request
type.
"""
from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field

from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.tools import ToolDefinition


class UsageContext(BaseModel):
    """Who this request is billed/attributed to — feeds cost tracking and
    rate limiting. All optional so the AI Core is usable standalone."""

    organization_id: str | None = None
    user_id: str | None = None
    project_id: str | None = None


class RoutingHints(BaseModel):
    """Optional hints a caller can pass to influence the router without
    hardcoding a specific model. See router/strategies.py for how each
    field is consumed."""

    task: str | None = Field(default=None, description="e.g. 'summarization', 'coding', 'reasoning'")
    max_cost_usd: float | None = None
    max_latency_ms: float | None = None
    region: str | None = None
    prefer_provider: str | None = None
    experiment_bucket: str | None = Field(default=None, description="For canary/A-B routing")


class GenerationRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: uuid4().hex)
    messages: list[ChatMessage]
    model: str | None = Field(default=None, description="Explicit model id. If unset, the router chooses.")
    provider: str | None = Field(default=None, description="Explicit provider. If unset, the router chooses.")
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int | None = None
    stop: list[str] | None = None
    tools: list[ToolDefinition] | None = None
    tool_choice: str = Field(default="auto", description="'auto' | 'none' | 'required' | a tool name")
    response_format: dict[str, Any] | None = Field(
        default=None, description="e.g. {'type': 'json_object'} or {'type': 'json_schema', 'schema': {...}}"
    )
    stream: bool = False
    timeout_seconds: float | None = None
    max_retries: int | None = None
    usage_context: UsageContext = Field(default_factory=UsageContext)
    routing_hints: RoutingHints = Field(default_factory=RoutingHints)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EmbeddingRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: uuid4().hex)
    input: str | list[str]
    model: str | None = None
    provider: str | None = None
    usage_context: UsageContext = Field(default_factory=UsageContext)
    use_cache: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)

    def as_list(self) -> list[str]:
        return [self.input] if isinstance(self.input, str) else self.input
