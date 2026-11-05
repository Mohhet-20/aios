"""InferenceService — the AI Core gateway from the caller's point of view.
Every model call in the platform funnels through here, which is what makes
provider-swapping (the whole point of the AI Core abstraction) possible:
this service depends on `ModelProviderAdapter`, never on a specific
provider's SDK. Today that adapter is `StubModelProvider` per the current
scope boundary — see `app.infrastructure.ai_providers` for the swap plan.
"""

from __future__ import annotations

import time

from app.domain.events.events import InferenceCompleted, InferenceRequested
from app.events.bus import EventBus
from app.infrastructure.ai_providers.base import GenerationRequest, GenerationResponse, ModelProviderAdapter
from app.monitoring.metrics import INFERENCE_REQUESTS


class InferenceService:
    def __init__(self, provider: ModelProviderAdapter, event_bus: EventBus):
        self.provider = provider
        self.event_bus = event_bus

    async def generate(
        self, model_id: str, messages: list[dict], temperature: float = 0.7
    ) -> GenerationResponse:
        request = GenerationRequest(model_id=model_id, messages=messages, temperature=temperature)
        await self.event_bus.publish(InferenceRequested(request_id=model_id, model_id=model_id))

        start = time.perf_counter()
        try:
            response = await self.provider.generate(request)
        except Exception:
            INFERENCE_REQUESTS.labels(model_id=model_id, status="error").inc()
            raise

        INFERENCE_REQUESTS.labels(model_id=model_id, status="success").inc()
        await self.event_bus.publish(
            InferenceCompleted(
                request_id=model_id,
                model_id=model_id,
                latency_ms=(time.perf_counter() - start) * 1000,
                token_count=response.prompt_tokens + response.completion_tokens,
            )
        )
        return response

    async def stream(self, model_id: str, messages: list[dict], temperature: float = 0.7):
        request = GenerationRequest(model_id=model_id, messages=messages, temperature=temperature)
        async for chunk in self.provider.stream(request):
            yield chunk
