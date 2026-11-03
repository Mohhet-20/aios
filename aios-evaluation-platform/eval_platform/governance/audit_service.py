"""AuditService: one consolidated write-path for every governance-
relevant action this platform takes — evaluation/dataset edits,
lifecycle transitions, RBAC grants/revokes, alert resolutions. A single
`ep_audit_log` table, not one per domain, so "show me everything that
happened to this resource" or "show me everything this actor did" is
always one query."""
from __future__ import annotations

from eval_platform.models.governance import AuditLogEntryModel
from eval_platform.repositories.registry import RepositoryRegistry


class AuditService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record(
        self, actor_id: str, *, action: str, resource_type: str, resource_id: str,
        before: dict | None = None, after: dict | None = None,
    ) -> AuditLogEntryModel:
        return await self.repos.audit_log.add(AuditLogEntryModel(
            actor_id=actor_id, action=action, resource_type=resource_type, resource_id=resource_id, before=before, after=after,
        ))

    async def list_for_resource(self, resource_type: str, resource_id: str) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log.list_for_resource(resource_type, resource_id)

    async def list_for_actor(self, actor_id: str) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log.list_for_actor(actor_id)
