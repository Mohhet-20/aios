"""RetentionService: applies `Settings.audit_log_retention_days` /
`login_history_retention_days` by hard-deleting rows older than the
retention window. Deliberately a hard delete, not a soft delete — a
retention policy's entire point is that the data stops existing after
its window, which a `SoftDeleteMixin` flag would defeat. Designed to
be invoked from a scheduled sweep (same "idempotent, safe to call on a
timer" shape as `SessionService.sweep_expirations`/`ApiKeyService.
sweep_expirations`)."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import delete

from identity_platform.config.settings import Settings, get_settings
from identity_platform.database.base import utcnow
from identity_platform.models.governance import AuditLogEntryModel
from identity_platform.models.session import LoginHistoryModel
from identity_platform.repositories.registry import RepositoryRegistry


class RetentionService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def purge_expired_audit_logs(self) -> int:
        cutoff = utcnow() - timedelta(days=self.settings.audit_log_retention_days)
        result = await self.repos.session.execute(delete(AuditLogEntryModel).where(AuditLogEntryModel.created_at < cutoff))
        return result.rowcount or 0

    async def purge_expired_login_history(self) -> int:
        cutoff = utcnow() - timedelta(days=self.settings.login_history_retention_days)
        result = await self.repos.session.execute(delete(LoginHistoryModel).where(LoginHistoryModel.created_at < cutoff))
        return result.rowcount or 0

    async def run_all(self) -> dict[str, int]:
        return {
            "audit_log_purged": await self.purge_expired_audit_logs(),
            "login_history_purged": await self.purge_expired_login_history(),
        }
