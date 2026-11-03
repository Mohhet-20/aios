"""AuditService — the governance-facing read/write surface over the one
consolidated `AuditLogEntryModel` table that already serves memory
lifecycle events (`MemoryService`) and now governance events (grants,
revocations, access denials) too, rather than a second audit table.
Append-only by construction (the repository exposes no update/delete)."""
from __future__ import annotations

from memory_platform.database.base import new_uuid
from memory_platform.models.governance import AuditLogEntryModel
from memory_platform.repositories.registry import RepositoryRegistry


class AuditService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record(self, *, actor_id: str, action: str, resource_type: str, resource_id: str, before: dict | None = None, after: dict | None = None) -> AuditLogEntryModel:
        return await self.repos.audit_log.add(AuditLogEntryModel(
            id=new_uuid(), actor_id=actor_id, action=action, resource_type=resource_type, resource_id=resource_id, before=before, after=after,
        ))

    async def record_access_denied(self, *, actor_id: str, resource_type: str, resource_id: str, reason: str) -> AuditLogEntryModel:
        return await self.record(actor_id=actor_id, action="access.denied", resource_type=resource_type, resource_id=resource_id, after={"reason": reason})

    async def get_audit_trail(self, resource_type: str, resource_id: str, *, limit: int = 100) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log.list_for_resource(resource_type, resource_id, limit=limit)
