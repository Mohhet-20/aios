"""The service's one clock. Every timestamp (ORM defaults, domain state changes, service code) comes
from here.

``utc_now()`` is strictly increasing within the process: rows written in the same clock tick (common
on Windows, whose clock is coarse) would otherwise share a timestamp, and "newest first" / "latest"
queries order by time alone, so their order would be arbitrary. Because every timestamp has this one
source, durations computed from two of them are never negative. Calling ``datetime.now()`` directly
elsewhere would break that guarantee.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

_lock = threading.Lock()
_last = datetime.min.replace(tzinfo=timezone.utc)


def utc_now() -> datetime:
    global _last
    with _lock:
        now = datetime.now(timezone.utc)
        if now <= _last:
            now = _last + timedelta(microseconds=1)
        _last = now
        return now
