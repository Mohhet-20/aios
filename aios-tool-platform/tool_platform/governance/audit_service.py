"""Append-only audit log — every governance-relevant action (grants,
revocations, approvals/rejections, sensitive executions, credential
rotations) gets one row here. No update/delete path is exposed on
purpose; `AuditLogEntryModel` itself has no AuditMixin/SoftDeleteMixin
for the same reason — the trail has to stay tamper-evident by omission
of any mutation API, not by convention."""
from __future__ import annotations

from tool_platform.models.governance import AuditLogEntryModel
from tool_platform.repositories.registry import RepositoryRegistry


class AuditService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record(
        self, actor_id: str, action: str, resource_type: str, resource_id: str, *,
        before: dict | None = None, after: dict | None = None,
    ) -> AuditLogEntryModel:
        return await self.repos.audit_log.add(AuditLogEntryModel(
            actor_id=actor_id, action=action, resource_type=resource_type, resource_id=resource_id,
            before=before, after=after,
        ))

    async def list_for_resource(self, resource_type: str, resource_id: str, *, limit: int = 100) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log.list_for_resource(resource_type, resource_id, limit=limit)

    async def list_for_actor(self, actor_id: str, *, limit: int = 100) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log.list_for_actor(actor_id, limit=limit)
