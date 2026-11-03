"""Recurring failure pattern tracking. `record_occurrence` is a
get-or-increment upsert keyed on (tenant_id, pattern_type, subject_ref)
behind a commit-spanning `asyncio.Lock` — the same pattern established
across every prior AIOS platform, with the mid-lock commit needed so a
waiting caller's read can't observe a still-uncommitted insert/update
from a separate DB connection. A pattern is "recurring" once its
occurrence count crosses `failure_pattern_min_occurrences`."""
from __future__ import annotations

import asyncio
from collections import defaultdict


from quality_platform.config.settings import get_settings
from quality_platform.models.failure_analysis import FailurePatternModel
from quality_platform.repositories.registry import RepositoryRegistry
from quality_platform.clock import utc_now


class FailurePatternService:
    _record_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def record_occurrence(
        self, tenant_id: str, *, pattern_type: str, subject_ref: str, details: dict | None = None
    ) -> FailurePatternModel:
        lock_key = f"{tenant_id}:{pattern_type}:{subject_ref}"
        async with self._record_locks[lock_key]:
            existing = await self.repos.failure_patterns.get_for_subject(tenant_id, pattern_type, subject_ref)
            now = utc_now()
            if existing is not None:
                existing.occurrences += 1
                existing.last_seen_at = now
                if details:
                    existing.details = {**existing.details, **details}
                existing = await self.repos.failure_patterns.update(existing)
                await self.repos.session.commit()
                return existing
            pattern = FailurePatternModel(
                tenant_id=tenant_id, pattern_type=pattern_type, subject_ref=subject_ref,
                occurrences=1, first_seen_at=now, last_seen_at=now, details=details or {},
            )
            pattern = await self.repos.failure_patterns.add(pattern)
            await self.repos.session.commit()
            return pattern

    def is_recurring(self, pattern: FailurePatternModel) -> bool:
        return pattern.occurrences >= self.settings.failure_pattern_min_occurrences

    async def list_patterns(self, tenant_id: str, *, pattern_type: str | None = None, min_occurrences: int = 1) -> list[FailurePatternModel]:
        return await self.repos.failure_patterns.list_for_tenant(tenant_id, pattern_type=pattern_type, min_occurrences=min_occurrences)
