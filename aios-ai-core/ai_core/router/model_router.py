"""The Model Router: turns a GenerationRequest into an ordered candidate
chain (primary pick + fallbacks) by running the registry's usable models
through a RoutingPolicy's strategy pipeline. The execution engine is the
only consumer of `route()` — it walks the returned chain in order, trying
the next candidate whenever one fails.
"""
from __future__ import annotations

from ai_core.registry.model_metadata import ModelMetadata
from ai_core.registry.model_registry import ModelRegistry
from ai_core.router.policy import RoutingPolicy
from ai_core.schemas.enums import Capability, ContentType
from ai_core.schemas.requests import EmbeddingRequest, GenerationRequest
from ai_core.utils.exceptions import NoAvailableModelError


def _required_capabilities(request: GenerationRequest) -> set[Capability]:
    caps: set[Capability] = set()
    if request.stream:
        caps.add(Capability.STREAMING)
    if request.tools:
        caps.add(Capability.TOOL_CALLING)
    if request.response_format:
        caps.add(Capability.JSON_OUTPUT)
    for message in request.messages:
        if not isinstance(message.content, list):
            continue
        for part in message.content:
            if part.type in (ContentType.IMAGE_URL, ContentType.IMAGE_BASE64):
                caps.add(Capability.VISION)
            elif part.type == ContentType.AUDIO:
                caps.add(Capability.AUDIO_INPUT)
    return caps


class ModelRouter:
    def __init__(self, registry: ModelRegistry, *, policy: RoutingPolicy | None = None):
        self.registry = registry
        self.policy = policy or RoutingPolicy.default()

    def route(self, request: GenerationRequest) -> list[ModelMetadata]:
        """Returns the ordered fallback chain for a generation request.
        Explicit `request.provider`+`request.model` bypasses routing
        entirely (the caller knows exactly what they want); explicit
        `request.model` alone still runs the pipeline to pick the best
        *provider* among those serving that model name."""
        required = _required_capabilities(request)

        if request.provider and request.model:
            return [self.registry.get(request.provider, request.model)]

        if required:
            pool = self.registry.all()
            for cap in required:
                pool = [m for m in pool if cap in m.capabilities]
            pool = [m for m in pool if m.is_usable()]
        else:
            pool = [m for m in self.registry.all() if m.is_usable()]

        # Embedding-only models are never valid generate() candidates —
        # they're a distinct capability served through route_embedding(),
        # not an interchangeable "cheap chat model."
        pool = [m for m in pool if Capability.EMBEDDING not in m.capabilities]

        if request.model:
            pool = [m for m in pool if m.name == request.model]

        for strategy in self.policy.strategies:
            pool = strategy.apply(pool, request, required_capabilities=required)
            if not pool:
                break

        if not pool:
            raise NoAvailableModelError(
                f"No usable model satisfies request (required_capabilities={sorted(c.value for c in required)}, "
                f"model={request.model!r}, task={request.routing_hints.task!r})"
            )
        return pool[: self.policy.max_candidates]

    def route_embedding(self, request: EmbeddingRequest) -> list[ModelMetadata]:
        if request.provider and request.model:
            return [self.registry.get(request.provider, request.model)]
        pool = self.registry.list_by_capability(Capability.EMBEDDING)
        if request.model:
            pool = [m for m in pool if m.name == request.model]
        pool = sorted(pool, key=lambda m: m.priority)
        if not pool:
            raise NoAvailableModelError(f"No usable embedding model (model={request.model!r})")
        return pool[: self.policy.max_candidates]
