"""AuditService: an immutable log entry per sensitive action (actor,
action, resource, workspace, metadata, timestamp) — the same
append-only, never-mutated pattern as `ActivityEventModel`, but a
distinct table because audit and activity serve different audiences
and retention rules (audit is compliance/security evidence with its
own retention policy; activity is a product feed users browse)."""
from __future__ import annotations

from collaboration_platform.models.governance import AuditLogEntryModel
from collaboration_platform.repositories.registry import RepositoryRegistry


class AuditService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record(
        self, *, actor_id: str, action: str, resource_type: str, resource_id: str, workspace_id: str | None = None,
        audit_metadata: dict | None = None,
    ) -> AuditLogEntryModel:
        return await self.repos.audit_log_entries.add(AuditLogEntryModel(
            actor_id=actor_id, action=action, resource_type=resource_type, resource_id=resource_id,
            workspace_id=workspace_id, audit_metadata=audit_metadata or {},
        ))

    async def list_for_workspace(self, workspace_id: str, *, action: str | None = None, limit: int = 200) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log_entries.list_for_workspace(workspace_id, action=action, limit=limit)

    async def list_for_actor(self, actor_id: str, *, limit: int = 200) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log_entries.list_for_actor(actor_id, limit=limit)
