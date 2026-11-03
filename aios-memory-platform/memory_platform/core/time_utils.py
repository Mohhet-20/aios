"""Shared datetime helpers. SQLite has no native datetime type — the
sqlite dialect stores our tz-aware timestamps as naive TEXT, and a value
read back via a fresh row hydration (rather than served from the
session's identity map) loses its tzinfo, while a value still in the
identity map keeps it. Every timestamp in this platform is UTC by
convention regardless of which path served it, so callers that compare
or subtract timestamps coming from the database should normalize
through `as_aware_utc` first rather than assume awareness.
"""
from __future__ import annotations

from datetime import datetime, timezone


def as_aware_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
