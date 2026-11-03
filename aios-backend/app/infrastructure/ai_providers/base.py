"""Model provider adapter interface — the AI Core abstraction from Phase
1's architecture. Every engine that needs a model (InferenceService,
EmbeddingService, EvaluationService's LLM-as-judge grader) depends on this
interface, never on a provider SDK directly.

Per this phase's scope boundary ("do NOT implement AI model logic
yet"), no concrete adapter here calls a real provider. `StubModelProvider`
returns deterministic, clearly-labeled placeholder output so the rest of the
platform (routing, streaming, token accounting, event emission) can be built
and tested end-to-end today. Implementing `AnthropicProvider`/`OpenAIProvider`
against this same interface is the entire scope of the next phase — nothing
above this file changes when that happens.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass


@dataclass
class GenerationRequest:
    model_id: str
    messages: list[dict]  # [{"role": "user"|"assistant"|"system", "content": str}]
    temperature: float = 0.7
    max_tokens: int = 1024


@dataclass
class GenerationChunk:
    delta: str
    is_final: bool = False
    finish_reason: str | None = None


@dataclass
class GenerationResponse:
    content: str
    model_id: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float


class ModelProviderAdapter(ABC):
    @abstractmethod
    async def generate(self, request: GenerationRequest) -> GenerationResponse: ...

    @abstractmethod
    async def stream(self, request: GenerationRequest) -> AsyncIterator[GenerationChunk]: ...

    @abstractmethod
    async def embed(self, model_id: str, texts: list[str]) -> list[list[float]]: ...
