"""Append-only audit log: every view/create/update/delete/export/share
against a governed resource gets a row here. This is deliberately a
thin, validate-and-persist service -- the value is that every other
service in this platform can call `record()` without needing its own
audit-log opinions."""
from __future__ import annotations

from analytics_platform.core.exceptions import ValidationError
from analytics_platform.domain.enums import AuditActionType
from analytics_platform.models.security import AuditLogEntryModel
from analytics_platform.repositories.registry import RepositoryRegistry


class AuditLogService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    def _assert_valid_action(self, action_type: str) -> None:
        if action_type not in {a.value for a in AuditActionType}:
            raise ValidationError(f"'{action_type}' is not a recognized audit action type")

    async def record(
        self, tenant_id: str, *, action_type: str, resource_type: str, actor_id: str | None = None,
        resource_id: str | None = None, details: dict | None = None,
    ) -> AuditLogEntryModel:
        self._assert_valid_action(action_type)
        entry = AuditLogEntryModel(
            tenant_id=tenant_id, actor_id=actor_id, action_type=action_type, resource_type=resource_type,
            resource_id=resource_id, details=details or {},
        )
        return await self.repos.audit_log.add(entry)

    async def list_recent(self, tenant_id: str, *, action_type: str | None = None, limit: int = 200) -> list[AuditLogEntryModel]:
        return await self.repos.audit_log.list_recent(tenant_id, action_type=action_type, limit=limit)
