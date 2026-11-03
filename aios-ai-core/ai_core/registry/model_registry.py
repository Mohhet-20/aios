"""Centralized, in-memory Model Registry. Production deployments can swap
the storage backend (e.g. Postgres-backed, synced from an admin UI) behind
this same interface — nothing outside this file needs to change, callers
only ever use `ModelRegistry`.
"""
from __future__ import annotations

from ai_core.registry.model_metadata import ModelMetadata
from ai_core.schemas.enums import Capability, ModelStatus
from ai_core.utils.exceptions import ModelNotFoundError


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[str, ModelMetadata] = {}

    def register(self, model: ModelMetadata) -> None:
        self._models[model.key] = model

    def register_many(self, models: list[ModelMetadata]) -> None:
        for m in models:
            self.register(m)

    def get(self, provider: str, name: str) -> ModelMetadata:
        key = f"{provider}:{name}"
        model = self._models.get(key)
        if model is None:
            raise ModelNotFoundError(f"No registered model for '{key}'")
        return model

    def get_by_key(self, key: str) -> ModelMetadata:
        model = self._models.get(key)
        if model is None:
            raise ModelNotFoundError(f"No registered model for '{key}'")
        return model

    def unregister(self, provider: str, name: str) -> None:
        self._models.pop(f"{provider}:{name}", None)

    def all(self) -> list[ModelMetadata]:
        return list(self._models.values())

    def list_by_provider(self, provider: str) -> list[ModelMetadata]:
        return [m for m in self._models.values() if m.provider == provider]

    def list_by_capability(self, capability: Capability, *, only_usable: bool = True) -> list[ModelMetadata]:
        return [
            m for m in self._models.values()
            if m.supports(capability) and (not only_usable or m.is_usable())
        ]

    def list_by_tag(self, tag: str, *, only_usable: bool = True) -> list[ModelMetadata]:
        return [m for m in self._models.values() if tag in m.tags and (not only_usable or m.is_usable())]

    def update_status(self, provider: str, name: str, status: ModelStatus) -> None:
        self.get(provider, name).status = status

    def update_latency(self, provider: str, name: str, latency_ms: float, *, alpha: float = 0.3) -> None:
        """Exponential moving average so one slow request doesn't
        permanently poison latency-aware routing."""
        model = self.get(provider, name)
        if model.average_latency_ms is None:
            model.average_latency_ms = latency_ms
        else:
            model.average_latency_ms = alpha * latency_ms + (1 - alpha) * model.average_latency_ms
