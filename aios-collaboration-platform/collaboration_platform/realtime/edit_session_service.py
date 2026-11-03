"""EditSessionService: tracks who is actively editing an asset and
enforces `max_concurrent_editors_per_asset`. This is deliberately a
*soft* collaborative-editing cap (unlike a hard single-writer lock) —
enterprise collaboration tools let multiple people co-edit the same
document; the cap exists to bound how many concurrent edit streams the
conflict-resolution layer has to reconcile, not to serialize writers.

The read-count -> insert sequence in `start_session` is a
check-then-act critical section spanning multiple statements, proven
by a stress test to oversell the quota under real concurrency (10
concurrent starts against a limit of 3 all succeeded). It's serialized
per-asset via an in-process `asyncio.Lock`, held across the read,
insert, *and* commit — the lock has to span the commit specifically,
because each caller owns its own DB connection and SQLite doesn't make
one connection's write visible to another until it commits. This is
the exact same fix (and the exact same reasoning) as the Identity
Platform's `SessionService.create_session` concurrent-session-limit
race: single-process-scope, documented tradeoff, same as
`RateLimitService`'s precedent."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from collaboration_platform.config.settings import Settings, get_settings
from collaboration_platform.core.exceptions import NotFoundError, QuotaExceededError
from collaboration_platform.database.base import utcnow
from collaboration_platform.models.presence import EditSessionModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class EditSessionService:
    # Per-asset locks, shared across all EditSessionService instances
    # within this process (keyed on asset_id, not on `self`).
    _asset_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def start_session(self, asset_id: str, user_id: str, *, base_version_id: str | None = None) -> EditSessionModel:
        await self.repos.assets.get_or_404(asset_id)
        async with self._asset_locks[asset_id]:
            active = await self.repos.edit_sessions.list_active_for_asset(asset_id)
            if len(active) >= self.settings.max_concurrent_editors_per_asset:
                raise QuotaExceededError(
                    f"asset '{asset_id}' already has {len(active)} concurrent editors "
                    f"(limit {self.settings.max_concurrent_editors_per_asset})"
                )
            session = await self.repos.edit_sessions.add(
                EditSessionModel(asset_id=asset_id, user_id=user_id, base_version_id=base_version_id)
            )
            await self.repos.session.commit()
        return session

    async def end_session(self, session_id: str) -> EditSessionModel:
        session = await self.repos.edit_sessions.get(session_id)
        if session is None:
            raise NotFoundError(f"edit session '{session_id}' not found")
        session.ended_at = utcnow()
        return await self.repos.edit_sessions.update(session)

    async def list_active_for_asset(self, asset_id: str) -> list[EditSessionModel]:
        return await self.repos.edit_sessions.list_active_for_asset(asset_id)
