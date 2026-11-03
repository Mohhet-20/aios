"""Embedding cache abstraction. `InMemoryEmbeddingCache` is the dev/test
default; production deployments swap in a Redis- or disk-backed
implementation behind the same two-method interface — nothing in
EmbeddingEngine changes."""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections import OrderedDict


class EmbeddingCache(ABC):
    @abstractmethod
    def get(self, key: str) -> list[float] | None: ...

    @abstractmethod
    def set(self, key: str, vector: list[float]) -> None: ...


class InMemoryEmbeddingCache(EmbeddingCache):
    def __init__(self, *, max_size: int = 10_000):
        self._store: OrderedDict[str, list[float]] = OrderedDict()
        self._max_size = max_size

    def get(self, key: str) -> list[float] | None:
        vector = self._store.get(key)
        if vector is not None:
            self._store.move_to_end(key)
        return vector

    def set(self, key: str, vector: list[float]) -> None:
        self._store[key] = vector
        self._store.move_to_end(key)
        if len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def __len__(self) -> int:
        return len(self._store)
