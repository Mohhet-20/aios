"""RateLimitService: an in-process sliding-window rate limiter keyed by
an arbitrary string (`f"{scope}:{identifier}"`, e.g.
`"password_reset:alice@example.com"` or `"login_ip:203.0.113.4"`).
In-process state is a deliberate scope decision: this platform has no
Redis/shared-cache dependency, so the limiter is correct for a single
process and becomes an approximation (each process enforces its own
window) once horizontally scaled — swapping the `_hits` dict for a
Redis sorted-set-based implementation later is a drop-in replacement
behind this same interface, without callers changing."""
from __future__ import annotations

import time
from collections import defaultdict

from identity_platform.core.exceptions import RateLimitExceededError


class RateLimitService:
    def __init__(self):
        self._hits: dict[str, list[float]] = defaultdict(list)

    def _key(self, scope: str, identifier: str) -> str:
        return f"{scope}:{identifier}"

    def check(self, scope: str, identifier: str, *, limit: int, window_seconds: int = 60) -> bool:
        """Records this attempt and returns whether it's within limit
        (does not raise — see `enforce` for the raising variant)."""
        key = self._key(scope, identifier)
        now = time.monotonic()
        cutoff = now - window_seconds
        recent = [t for t in self._hits[key] if t > cutoff]
        recent.append(now)
        self._hits[key] = recent
        return len(recent) <= limit

    def enforce(self, scope: str, identifier: str, *, limit: int, window_seconds: int = 60) -> None:
        if not self.check(scope, identifier, limit=limit, window_seconds=window_seconds):
            raise RateLimitExceededError(f"rate limit exceeded for '{scope}:{identifier}' ({limit} per {window_seconds}s)")

    def current_count(self, scope: str, identifier: str, *, window_seconds: int = 60) -> int:
        key = self._key(scope, identifier)
        cutoff = time.monotonic() - window_seconds
        return len([t for t in self._hits[key] if t > cutoff])

    def reset(self, scope: str, identifier: str) -> None:
        self._hits.pop(self._key(scope, identifier), None)


_default_limiter = RateLimitService()


def get_default_rate_limiter() -> RateLimitService:
    return _default_limiter
