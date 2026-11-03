"""Model metadata schema — the single source of truth the router, cost
tracker, and execution engine all read from to answer "can model X do Y,
and what does it cost."""
from __future__ import annotations

from pydantic import BaseModel, Field

from ai_core.schemas.enums import Capability, ModelStatus


class ModelPricing(BaseModel):
    input_cost_per_1m: float = 0.0
    output_cost_per_1m: float = 0.0
    cached_input_cost_per_1m: float = 0.0
    currency: str = "USD"


class ModelMetadata(BaseModel):
    provider: str
    name: str
    version: str = "latest"
    context_window: int = 8192
    max_output_tokens: int = 4096
    capabilities: set[Capability] = Field(default_factory=set)
    pricing: ModelPricing = Field(default_factory=ModelPricing)
    status: ModelStatus = ModelStatus.AVAILABLE
    region: str | None = None
    priority: int = Field(default=100, description="Lower = preferred. Used by priority routing.")
    tags: list[str] = Field(default_factory=list, description="Free-form labels for task-based routing, e.g. ['coding', 'reasoning'].")
    average_latency_ms: float | None = Field(default=None, description="Rolling average, updated by the router's latency tracker.")

    @property
    def key(self) -> str:
        return f"{self.provider}:{self.name}"

    def supports(self, capability: Capability) -> bool:
        return capability in self.capabilities

    def is_usable(self) -> bool:
        return self.status in (ModelStatus.AVAILABLE, ModelStatus.DEGRADED)
