"""Collaboration: an append-only audit trail. Every write worth
tracing (page published, review decided, role assigned, article
archived) gets logged here by its calling service — this service only
knows how to write and query entries, not which actions are
audit-worthy, so the "what gets logged" decision stays with each
domain service rather than being centralized into a brittle registry."""
from __future__ import annotations

from docs_platform.models.collaboration import AuditLogEntryModel
from docs_platform.repositories.registry import RepositoryRegistry


class AuditLogService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def log_action(self, tenant_id: str, *, actor_id: str | None, action: str, target_ref: str, details: dict | None = None) -> AuditLogEntryModel:
        entry = AuditLogEntryModel(tenant_id=tenant_id, actor_id=actor_id, action=action, target_ref=target_ref, details=details or {})
        return await self.repos.audit_log_entries.add(entry)

    async def list_for_target(self, tenant_id: str, target_ref: str, *, limit: int = 100) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log_entries.list_for_target(tenant_id, target_ref, limit=limit)

    async def list_recent(self, tenant_id: str, *, limit: int = 100) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log_entries.list_recent(tenant_id, limit=limit)
