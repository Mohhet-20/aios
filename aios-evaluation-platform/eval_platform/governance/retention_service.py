"""RetentionService: the sweep a background job calls on a timer to
purge `ObservabilityEventModel` rows past the configured retention
window (`settings.observability_event_retention_days`) — the same
idempotent batched-sweep shape used for expiration/cleanup jobs across
this AIOS build. Hard-deletes (observability events carry no soft-
delete column and no downstream aggregate depends on a purged row
staying queryable)."""
from __future__ import annotations

from datetime import timedelta

from eval_platform.config.settings import get_settings
from eval_platform.repositories.registry import RepositoryRegistry
from eval_platform.clock import utc_now


class RetentionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def sweep_observability_events(self, *, batch_size: int = 1000) -> int:
        settings = get_settings()
        cutoff = utc_now() - timedelta(days=settings.observability_event_retention_days)
        stale = await self.repos.observability_events.list_older_than(older_than=cutoff, limit=batch_size)
        for event in stale:
            await self.repos.observability_events.delete(event, hard=True)
        return len(stale)
