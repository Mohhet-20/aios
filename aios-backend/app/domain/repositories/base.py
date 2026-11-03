"""Generic repository port (interface). Concrete infrastructure
implementations (`app.repositories.*`) implement this against SQLAlchemy;
services depend on this abstraction, never on SQLAlchemy directly — the
Dependency Inversion half of Clean Architecture.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class AbstractRepository(ABC, Generic[T]):
    @abstractmethod
    async def get(self, id: str) -> T | None: ...

    @abstractmethod
    async def add(self, entity: T) -> T: ...

    @abstractmethod
    async def update(self, entity: T) -> T: ...

    @abstractmethod
    async def delete(self, id: str, *, soft: bool = True) -> None: ...

    @abstractmethod
    async def list(self, **filters) -> list[T]: ...
