"""SyncService: the optimistic-concurrency guard every write-path in
this platform that mutates asset content funnels through, plus
offline/connection-recovery helpers. `assert_not_stale` is the same
compare-and-swap idea as a database row's `version` column
(`VersionedMixin`/`ConcurrentModificationError` in `repositories/base.py`)
applied at the asset-content level: a caller declares the version they
last saw, and if the asset has moved on since, the write is rejected
instead of silently clobbering someone else's change. `VersionService`
(built next) calls this before creating a new version row."""
from __future__ import annotations

from collaboration_platform.core.exceptions import StaleWriteError
from collaboration_platform.repositories.registry import RepositoryRegistry


class SyncService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def assert_not_stale(self, asset_id: str, expected_version_id: str | None) -> None:
        """Raises `StaleWriteError` if the asset's current version has
        moved on from what the caller last saw. `expected_version_id is
        None` means "I'm creating the first version" and is always
        accepted as long as the asset genuinely has no current version
        yet — a caller claiming a fresh start against an asset that
        already has content is still a stale write."""
        asset = await self.repos.assets.get_or_404(asset_id)
        if asset.current_version_id != expected_version_id:
            raise StaleWriteError(
                f"asset '{asset_id}' has moved on since version '{expected_version_id}' "
                f"(current version is '{asset.current_version_id}') — reload and reapply your change"
            )

    async def resume_offline_session(self, edit_session_id: str) -> dict:
        """Called when a client reconnects after being offline; reports
        whether the asset moved on while the client was disconnected so
        the client can decide whether to prompt for a merge before
        resubmitting queued offline edits."""
        session = await self.repos.edit_sessions.get_or_404(edit_session_id)
        asset = await self.repos.assets.get_or_404(session.asset_id)
        stale = session.base_version_id != asset.current_version_id
        return {
            "edit_session_id": session.id, "asset_id": asset.id, "is_stale": stale,
            "session_base_version_id": session.base_version_id, "current_version_id": asset.current_version_id,
        }

    async def reconnect_presence(self, connection_id: str, asset_id: str, user_id: str) -> None:
        """Connection recovery: if a presence row for this exact
        connection id still exists (the client reconnected before the
        stale-session sweep cleaned it up), this is a no-op heartbeat;
        otherwise the caller should `PresenceService.join` a fresh
        session — this method only answers "do I need to rejoin"."""
        existing = await self.repos.presence_sessions.get_by_connection_id(connection_id)
        if existing is None:
            return None
        return existing
