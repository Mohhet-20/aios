"""SQLite does not have a native timezone-aware datetime type: a column
declared `DateTime(timezone=True)` round-trips as a naive `datetime` when
read back through aiosqlite, even though it was written from an aware UTC
value (Postgres's `timestamptz`, by contrast, round-trips correctly aware).
Every value this codebase ever writes to such a column is UTC, so
`ensure_aware_utc` is the one place that assumption is encoded — call it on
any datetime read from the database before comparing or subtracting it
against a freshly-created `utc_now()`, so the same code
behaves identically on SQLite (dev/test) and Postgres (production).
"""

from datetime import datetime, timezone


def ensure_aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
