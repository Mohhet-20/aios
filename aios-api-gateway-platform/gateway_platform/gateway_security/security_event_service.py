"""Security events: an append-only feed any policy, filter, or
detector in this module can write to. Every enforcement service above
(IP filter, geo filter, threat detection) is expected to call
`record_event` when it denies or flags something, giving operators one
place to look for "what did the gateway's security layer do."""
from __future__ import annotations

from gateway_platform.domain.enums import SecurityEventSeverity
from gateway_platform.models.security import SecurityEventModel
from gateway_platform.repositories.registry import RepositoryRegistry


class SecurityEventService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record_event(
        self, tenant_id: str, *, event_type: str, severity: str = SecurityEventSeverity.INFO.value,
        source_ip: str | None = None, details: dict | None = None,
    ) -> SecurityEventModel:
        SecurityEventSeverity(severity)  # validates the value
        event = SecurityEventModel(
            tenant_id=tenant_id, event_type=event_type, severity=severity, source_ip=source_ip, details=details or {},
        )
        return await self.repos.security_events.add(event)

    async def list_recent(self, tenant_id: str, *, severity: str | None = None, limit: int = 200) -> list[SecurityEventModel]:
        return await self.repos.security_events.list_recent(tenant_id, severity=severity, limit=limit)
