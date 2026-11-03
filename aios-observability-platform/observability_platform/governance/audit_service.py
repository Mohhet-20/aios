"""Immutable audit log — distinct from the operational data this
platform observes (logs/metrics/traces): this is a record of actions
taken *against the observability platform itself* (who acknowledged
that alert, who changed this retention policy, who granted admin
access), the same separation the Collaboration Platform draws between
its audit log and its product-facing activity feed."""
from __future__ import annotations

from datetime import timedelta

from observability_platform.config.settings import Settings, get_settings
from observability_platform.database.base import utcnow
from observability_platform.models.governance import AuditLogEntryModel
from observability_platform.repositories.registry import RepositoryRegistry

RESOURCE_TYPE = "audit_log"


class AuditService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def record(
        self, tenant_id: str, *, actor_id: str | None, action: str, resource_type: str,
        resource_id: str | None = None, details: dict | None = None,
    ) -> AuditLogEntryModel:
        entry = AuditLogEntryModel(
            tenant_id=tenant_id, actor_id=actor_id, action=action, resource_type=resource_type,
            resource_id=resource_id, details=details or {},
        )
        return await self.repos.audit_log_entries.add(entry)

    async def list_recent(self, tenant_id: str, *, limit: int = 200) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log_entries.list_for_tenant(tenant_id, limit=limit)

    async def sweep_expired(self, tenant_id: str) -> int:
        policy = await self.repos.retention_policies.get_for_resource(tenant_id, RESOURCE_TYPE)
        retention_days = policy.retention_days if policy and policy.is_enabled else self.settings.audit_log_retention_days
        cutoff = utcnow() - timedelta(days=retention_days)
        return await self.repos.audit_log_entries.delete_older_than(tenant_id, cutoff)
