"""SecurityEventService: the write/read path for `SecurityEventModel` —
every other module in this package (rate limiting, restrictions, risk
scoring) that detects something noteworthy calls `record_event` rather
than writing the model directly, so severity/detail conventions stay
consistent in one place."""
from __future__ import annotations

from identity_platform.domain.enums import SecurityEventSeverity, SecurityEventType
from identity_platform.models.security import SecurityEventModel
from identity_platform.repositories.registry import RepositoryRegistry


class SecurityEventService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record_event(
        self, *, event_type: SecurityEventType, severity: SecurityEventSeverity,
        organization_id: str | None = None, user_id: str | None = None, details: dict | None = None,
    ) -> SecurityEventModel:
        return await self.repos.security_events.add(SecurityEventModel(
            organization_id=organization_id, user_id=user_id, event_type=event_type.value,
            severity=severity.value, details=details or {},
        ))

    async def resolve_event(self, event_id: str) -> SecurityEventModel:
        event = await self.repos.security_events.get_or_404(event_id)
        event.resolved = True
        return await self.repos.security_events.update(event)

    async def list_unresolved(self, organization_id: str | None = None) -> list[SecurityEventModel]:
        return await self.repos.security_events.list_unresolved(organization_id)

    async def list_for_user(self, user_id: str, *, limit: int = 50) -> list[SecurityEventModel]:
        return await self.repos.security_events.list_for_user(user_id, limit=limit)

    async def list_for_organization(self, organization_id: str, *, severity: SecurityEventSeverity | None = None, limit: int = 100) -> list[SecurityEventModel]:
        return await self.repos.security_events.list_for_organization(
            organization_id, severity=severity.value if severity else None, limit=limit,
        )
