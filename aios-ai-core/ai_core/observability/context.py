"""Correlation-id propagation via contextvars. Mirrors the pattern used
elsewhere in the AIOS platform (same idea as the backend's request/
correlation-id middleware) but kept self-contained here — the AI Core is a
standalone deployable and shouldn't import from the backend package."""
from __future__ import annotations

from contextvars import ContextVar
from uuid import uuid4

_correlation_id_ctx: ContextVar[str] = ContextVar("ai_core_correlation_id", default="")


def new_correlation_id() -> str:
    return uuid4().hex


def set_correlation_id(correlation_id: str | None = None) -> str:
    value = correlation_id or new_correlation_id()
    _correlation_id_ctx.set(value)
    return value


def get_correlation_id() -> str:
    return _correlation_id_ctx.get()
