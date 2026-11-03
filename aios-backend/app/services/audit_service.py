"""AuditService — the only writer of `AuditLogModel` rows besides the event
handler in `app.events.handlers` (which covers actions that emit domain
events already). Services that need to audit an action *not* already
covered by a domain event call this directly.
"""

from __future__ import annotations

from app.models.audit import AuditLogModel
from app.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, repository: AuditRepository):
        self.repository = repository

    async def record(
        self,
        organization_id: str,
        actor: str,
        action: str,
        resource: str,
        status: str = "success",
        ip_address: str = "",
    ) -> AuditLogModel:
        entry = AuditLogModel(
            organization_id=organization_id,
            actor=actor,
            action=action,
            resource=resource,
            status=status,
            ip_address=ip_address,
        )
        return await self.repository.add(entry)

    async def list_recent(self, organization_id: str, limit: int = 100) -> list[AuditLogModel]:
        return await self.repository.list_recent(organization_id, limit)
