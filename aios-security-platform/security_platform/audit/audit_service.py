"""Immutable Audit Platform: a single generic `record()` primitive for
compliance-grade evidence — approval history, configuration changes,
policy changes, security decisions, prompt/workflow history, model
and tool usage, and general compliance evidence. Unlike the ten
narrowly-typed security event categories, audit entries are
deliberately free-form (`action` is any dotted string the caller
chooses, e.g. "policy.updated", "approval.decided", "model.invoked")
because the audit log's job is to be a complete, queryable record of
*everything that happened*, not to classify it into a fixed taxonomy.
Entries are never updated or deleted except by an explicit,
retention-driven sweep — nothing in this service exposes an update
path."""
from __future__ import annotations

from datetime import timedelta

from security_platform.config.settings import Settings, get_settings
from security_platform.domain.entities import _now
from security_platform.models.events import AuditLogEntryModel
from security_platform.repositories.registry import RepositoryRegistry


class AuditService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def record(
        self, tenant_id: str, *, action: str, resource_type: str, resource_id: str | None = None,
        actor_id: str | None = None, details: dict | None = None,
    ) -> AuditLogEntryModel:
        return await self.repos.audit_log_entries.add(
            AuditLogEntryModel(
                tenant_id=tenant_id, actor_id=actor_id, action=action, resource_type=resource_type,
                resource_id=resource_id, details=details or {},
            )
        )

    async def history_for_resource(self, tenant_id: str, resource_type: str, resource_id: str, *, limit: int = 200) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log_entries.list_for_resource(tenant_id, resource_type, resource_id, limit=limit)

    async def history_for_actor(self, tenant_id: str, actor_id: str, *, limit: int = 200) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log_entries.list_for_actor(tenant_id, actor_id, limit=limit)

    async def recent(self, tenant_id: str, *, limit: int = 200) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log_entries.list_for_tenant(tenant_id, limit=limit)

    async def sweep_retention(self, tenant_id: str) -> int:
        cutoff = _now() - timedelta(days=self.settings.audit_log_retention_days)
        return await self.repos.audit_log_entries.delete_older_than(tenant_id, cutoff)
