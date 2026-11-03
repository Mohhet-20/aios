"""Typed response models. Deliberately plain dataclasses built with
`from_dict` factories rather than a heavier validation library — this
mirrors the shape the platform's own REST layer serializes ORM rows
into (id/created_at/updated_at plus a domain-specific field set), so a
generated-client story (Code Generation Engine) can regenerate these
mechanically from the OpenAPI schema without changing this hand-written
reference implementation's public shape."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class ApiKey:
    id: str
    name: str
    key_prefix: str
    scopes: list[str]
    status: str
    rate_limit_per_minute: int
    expires_at: str | None = None
    last_used_at: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ApiKey":
        return cls(
            id=data["id"], name=data["name"], key_prefix=data["key_prefix"], scopes=list(data.get("scopes", [])),
            status=data["status"], rate_limit_per_minute=data.get("rate_limit_per_minute", 60),
            expires_at=data.get("expires_at"), last_used_at=data.get("last_used_at"),
        )


@dataclass
class Plugin:
    id: str
    name: str
    category: str
    description: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Plugin":
        return cls(id=data["id"], name=data["name"], category=data["category"], description=data.get("description"))


@dataclass
class Page(Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        return max(1, (self.total + self.page_size - 1) // self.page_size)

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @classmethod
    def from_dict(cls, data: dict[str, Any], item_factory) -> "Page[T]":
        return cls(
            items=[item_factory(row) for row in data.get("items", [])],
            total=data.get("total", 0), page=data.get("page", 1), page_size=data.get("page_size", 50),
        )


@dataclass
class StreamEvent:
    """One line of a newline-delimited-JSON streaming response."""
    event_type: str
    data: dict[str, Any] = field(default_factory=dict)
