"""PresenceService: live "who's looking at this asset right now" state
— join/heartbeat/cursor-move/leave, plus a stale-session sweep for
connections that dropped without a clean disconnect (browser crash,
network loss). Presence rows are ephemeral by design (no soft-delete,
no audit trail) — this is real-time UI state, not a record anything
downstream needs to query historically."""
from __future__ import annotations

from datetime import timedelta

from collaboration_platform.config.settings import Settings, get_settings
from collaboration_platform.core.exceptions import NotFoundError
from collaboration_platform.database.base import utcnow
from collaboration_platform.domain.enums import PresenceStatus
from collaboration_platform.models.presence import PresenceSessionModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class PresenceService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def join(self, asset_id: str, user_id: str, *, connection_id: str, cursor_position: dict | None = None) -> PresenceSessionModel:
        await self.repos.assets.get_or_404(asset_id)
        return await self.repos.presence_sessions.add(PresenceSessionModel(
            asset_id=asset_id, user_id=user_id, connection_id=connection_id, cursor_position=cursor_position or {},
        ))

    async def heartbeat(self, connection_id: str) -> PresenceSessionModel:
        session = await self.repos.presence_sessions.get_by_connection_id(connection_id)
        if session is None:
            raise NotFoundError(f"presence connection '{connection_id}' not found")
        session.last_heartbeat_at = utcnow()
        if session.status == PresenceStatus.IDLE.value:
            session.status = PresenceStatus.ACTIVE.value
        return await self.repos.presence_sessions.update(session)

    async def update_cursor(self, connection_id: str, cursor_position: dict) -> PresenceSessionModel:
        session = await self.repos.presence_sessions.get_by_connection_id(connection_id)
        if session is None:
            raise NotFoundError(f"presence connection '{connection_id}' not found")
        session.cursor_position = cursor_position
        session.last_heartbeat_at = utcnow()
        return await self.repos.presence_sessions.update(session)

    async def mark_idle(self, connection_id: str) -> PresenceSessionModel:
        session = await self.repos.presence_sessions.get_by_connection_id(connection_id)
        if session is None:
            raise NotFoundError(f"presence connection '{connection_id}' not found")
        session.status = PresenceStatus.IDLE.value
        return await self.repos.presence_sessions.update(session)

    async def leave(self, connection_id: str) -> PresenceSessionModel:
        session = await self.repos.presence_sessions.get_by_connection_id(connection_id)
        if session is None:
            raise NotFoundError(f"presence connection '{connection_id}' not found")
        session.status = PresenceStatus.DISCONNECTED.value
        session.disconnected_at = utcnow()
        return await self.repos.presence_sessions.update(session)

    async def list_active(self, asset_id: str) -> list[PresenceSessionModel]:
        return await self.repos.presence_sessions.list_active_for_asset(asset_id)

    async def sweep_stale(self) -> list[PresenceSessionModel]:
        """Idempotent — safe to call on a timer. Any session whose last
        heartbeat is older than `presence_heartbeat_ttl_seconds` is
        treated as an unclean disconnect (the client never got to send
        a `leave`) and is force-disconnected."""
        cutoff = utcnow() - timedelta(seconds=self.settings.presence_heartbeat_ttl_seconds)
        stale = await self.repos.presence_sessions.list_stale(cutoff=cutoff)
        swept: list[PresenceSessionModel] = []
        for session in stale:
            session.status = PresenceStatus.DISCONNECTED.value
            session.disconnected_at = utcnow()
            await self.repos.presence_sessions.update(session)
            swept.append(session)
        return swept
