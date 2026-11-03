"""WorkingMemoryService — the agent's current focus within one session:
short-TTL, at most one active entry per scope (enforced by the WORKING
policy's `max_entries_per_scope=1`, via `MemoryService.create`'s
built-in enforcement — setting a new focus archives the old one)."""
from __future__ import annotations

from memory_platform.config.settings import Settings, get_settings
from memory_platform.domain.enums import MemoryStatus, MemoryType
from memory_platform.memory_core.memory_service import MemoryService
from memory_platform.models.memory_entry import MemoryEntryModel
from memory_platform.repositories.registry import RepositoryRegistry


class WorkingMemoryService:
    def __init__(self, repos: RepositoryRegistry, memory_service: MemoryService, *, settings: Settings | None = None):
        self.repos = repos
        self.memory_service = memory_service
        self.settings = settings or get_settings()

    async def set_focus(self, *, workspace_id: str, session_id: str, content: str, structured_content: dict | None = None, actor_id: str = "system") -> MemoryEntryModel:
        from datetime import timedelta

        ttl = self.settings.working_memory_ttl_seconds
        entry = await self.memory_service.create(
            workspace_id=workspace_id, memory_type=MemoryType.WORKING, scope_type="session", scope_id=session_id,
            content=content, actor_id=actor_id, structured_content=structured_content,
            retention_days_override=None,
        )
        # WORKING memory's TTL is short (seconds), finer-grained than the
        # day-resolution `retention_days` policy field, so it's set directly.
        entry.expires_at = entry.created_at + timedelta(seconds=ttl)
        await self.repos.memory_entries.update(entry)
        return entry

    async def get_focus(self, workspace_id: str, session_id: str) -> MemoryEntryModel | None:
        active = await self.repos.memory_entries.list_for_scope(
            workspace_id, "session", session_id, memory_type=MemoryType.WORKING.value, status=MemoryStatus.ACTIVE.value, limit=1,
        )
        return active[0] if active else None

    async def clear_focus(self, workspace_id: str, session_id: str, *, actor_id: str = "system") -> None:
        current = await self.get_focus(workspace_id, session_id)
        if current is not None:
            await self.memory_service.archive(current.id, actor_id=actor_id)
