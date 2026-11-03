"""EpisodicMemoryService — timestamped events (`occurred_at`, distinct
from `created_at`), queryable by time range. A thin service over
`MemoryService` for the one memory type where "when it happened" is a
first-class query dimension."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from memory_platform.domain.enums import MemoryType
from memory_platform.memory_core.memory_service import MemoryService
from memory_platform.models.memory_entry import MemoryEntryModel
from memory_platform.repositories.registry import RepositoryRegistry
from memory_platform.clock import utc_now


class EpisodicMemoryService:
    def __init__(self, repos: RepositoryRegistry, memory_service: MemoryService):
        self.repos = repos
        self.memory_service = memory_service

    async def record_event(
        self, *, workspace_id: str, scope_type: str, scope_id: str, description: str, occurred_at: datetime | None = None,
        structured_content: dict | None = None, actor_id: str = "system", importance_score: float | None = None,
    ) -> MemoryEntryModel:
        # An episode with no explicit `occurred_at` defaults to "now" —
        # leaving it null would silently make the event unqueryable by
        # `query_by_time_range`, which requires a non-null `occurred_at`.
        resolved_occurred_at = occurred_at if occurred_at is not None else utc_now()
        return await self.memory_service.create(
            workspace_id=workspace_id, memory_type=MemoryType.EPISODIC, scope_type=scope_type, scope_id=scope_id,
            content=description, actor_id=actor_id, structured_content=structured_content,
            occurred_at=resolved_occurred_at, importance_score=importance_score,
        )

    async def query_by_time_range(self, workspace_id: str, scope_type: str, scope_id: str, *, start: datetime, end: datetime) -> list[MemoryEntryModel]:
        stmt = select(MemoryEntryModel).where(
            MemoryEntryModel.workspace_id == workspace_id, MemoryEntryModel.scope_type == scope_type, MemoryEntryModel.scope_id == scope_id,
            MemoryEntryModel.memory_type == MemoryType.EPISODIC.value, MemoryEntryModel.occurred_at.is_not(None),
            MemoryEntryModel.occurred_at >= start, MemoryEntryModel.occurred_at <= end,
        ).order_by(MemoryEntryModel.occurred_at)
        return list((await self.repos.session.execute(stmt)).scalars().all())
