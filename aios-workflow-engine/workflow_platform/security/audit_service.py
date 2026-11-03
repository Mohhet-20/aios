"""AuditService: a thin, shared read/write API over the single
consolidated `AuditLogEntryModel` table — the same consolidation the
Memory and Agent Platforms used rather than modeling per-domain audit
tables. `ApprovalService` (Task 90) and `RBACService` (this task) both
write through this same table directly today; this service exists so a
future caller (Task 95's audit-log API endpoints) has one place to query
it rather than reaching into `repos.audit_log` itself."""
from __future__ import annotations

from workflow_platform.models.governance import AuditLogEntryModel
from workflow_platform.repositories.registry import RepositoryRegistry


class AuditService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record(self, actor_id: str, action: str, resource_type: str, resource_id: str, *, before: dict | None = None, after: dict | None = None) -> AuditLogEntryModel:
        return await self.repos.audit_log.add(AuditLogEntryModel(
            actor_id=actor_id, action=action, resource_type=resource_type, resource_id=resource_id, before=before, after=after,
        ))

    async def list_for_resource(self, resource_type: str, resource_id: str, *, limit: int = 100) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log.list_for_resource(resource_type, resource_id, limit=limit)

    async def list_for_actor(self, actor_id: str, *, limit: int = 100) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log.list_for_actor(actor_id, limit=limit)
