"""Security Events: an append-only feed covering every category this
platform cares about — authentication, authorization, policy/prompt/
tool/workflow violations, secrets access, risk changes, threat
detections, and administrative actions. `record_event` is the generic
primitive; the ten `record_*` convenience methods below map one-to-one
onto `SecurityEventType` and set a sensible default severity, matching
the same "one wrapper per enum value" convention used by the threat
detectors."""
from __future__ import annotations

from datetime import timedelta

from security_platform.config.settings import Settings, get_settings
from security_platform.domain.entities import _now
from security_platform.domain.enums import SecurityEventSeverity, SecurityEventType
from security_platform.models.events import SecurityEventModel
from security_platform.repositories.registry import RepositoryRegistry


class SecurityEventService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def record_event(
        self, tenant_id: str, event_type: str, *, description: str, severity: str = SecurityEventSeverity.INFO.value,
        actor_id: str | None = None, resource_type: str | None = None, resource_id: str | None = None, details: dict | None = None,
    ) -> SecurityEventModel:
        return await self.repos.security_events.add(
            SecurityEventModel(
                tenant_id=tenant_id, event_type=event_type, severity=severity, actor_id=actor_id,
                resource_type=resource_type, resource_id=resource_id, description=description, details=details or {},
            )
        )

    async def record_authentication(self, tenant_id: str, *, actor_id: str, success: bool, description: str, details: dict | None = None) -> SecurityEventModel:
        severity = SecurityEventSeverity.INFO.value if success else SecurityEventSeverity.MEDIUM.value
        return await self.record_event(tenant_id, SecurityEventType.AUTHENTICATION.value, description=description, severity=severity, actor_id=actor_id, details=details)

    async def record_authorization(self, tenant_id: str, *, actor_id: str, granted: bool, description: str, resource_type: str | None = None, resource_id: str | None = None) -> SecurityEventModel:
        severity = SecurityEventSeverity.INFO.value if granted else SecurityEventSeverity.MEDIUM.value
        return await self.record_event(tenant_id, SecurityEventType.AUTHORIZATION.value, description=description, severity=severity, actor_id=actor_id, resource_type=resource_type, resource_id=resource_id)

    async def record_policy_violation(self, tenant_id: str, *, actor_id: str | None, description: str, resource_type: str | None = None, resource_id: str | None = None, details: dict | None = None) -> SecurityEventModel:
        return await self.record_event(tenant_id, SecurityEventType.POLICY_VIOLATION.value, description=description, severity=SecurityEventSeverity.MEDIUM.value, actor_id=actor_id, resource_type=resource_type, resource_id=resource_id, details=details)

    async def record_prompt_violation(self, tenant_id: str, *, actor_id: str | None, description: str, resource_id: str | None = None, details: dict | None = None) -> SecurityEventModel:
        return await self.record_event(tenant_id, SecurityEventType.PROMPT_VIOLATION.value, description=description, severity=SecurityEventSeverity.MEDIUM.value, actor_id=actor_id, resource_type="prompt", resource_id=resource_id, details=details)

    async def record_tool_violation(self, tenant_id: str, *, actor_id: str | None, description: str, resource_id: str | None = None, details: dict | None = None) -> SecurityEventModel:
        return await self.record_event(tenant_id, SecurityEventType.TOOL_VIOLATION.value, description=description, severity=SecurityEventSeverity.MEDIUM.value, actor_id=actor_id, resource_type="tool", resource_id=resource_id, details=details)

    async def record_workflow_violation(self, tenant_id: str, *, actor_id: str | None, description: str, resource_id: str | None = None, details: dict | None = None) -> SecurityEventModel:
        return await self.record_event(tenant_id, SecurityEventType.WORKFLOW_VIOLATION.value, description=description, severity=SecurityEventSeverity.MEDIUM.value, actor_id=actor_id, resource_type="workflow", resource_id=resource_id, details=details)

    async def record_secrets_access(self, tenant_id: str, *, actor_id: str, description: str, resource_id: str | None = None, success: bool = True) -> SecurityEventModel:
        severity = SecurityEventSeverity.INFO.value if success else SecurityEventSeverity.HIGH.value
        return await self.record_event(tenant_id, SecurityEventType.SECRETS_ACCESS.value, description=description, severity=severity, actor_id=actor_id, resource_type="secret", resource_id=resource_id)

    async def record_risk_change(self, tenant_id: str, *, entity_type: str, entity_id: str, description: str, details: dict | None = None) -> SecurityEventModel:
        return await self.record_event(tenant_id, SecurityEventType.RISK_CHANGE.value, description=description, severity=SecurityEventSeverity.INFO.value, resource_type=entity_type, resource_id=entity_id, details=details)

    async def record_threat_detection(self, tenant_id: str, *, entity_type: str | None, entity_id: str | None, description: str, severity: str = SecurityEventSeverity.HIGH.value, details: dict | None = None) -> SecurityEventModel:
        return await self.record_event(tenant_id, SecurityEventType.THREAT_DETECTION.value, description=description, severity=severity, resource_type=entity_type, resource_id=entity_id, details=details)

    async def record_administrative_action(self, tenant_id: str, *, actor_id: str, description: str, resource_type: str | None = None, resource_id: str | None = None, details: dict | None = None) -> SecurityEventModel:
        return await self.record_event(tenant_id, SecurityEventType.ADMINISTRATIVE_ACTION.value, description=description, severity=SecurityEventSeverity.INFO.value, actor_id=actor_id, resource_type=resource_type, resource_id=resource_id, details=details)

    async def list_recent(self, tenant_id: str, *, event_type: str | None = None, severity: str | None = None, limit: int = 200):
        return await self.repos.security_events.list_recent(tenant_id, event_type=event_type, severity=severity, limit=limit)

    async def counts_by_type(self, tenant_id: str, *, since_hours: int | None = None) -> dict[str, int]:
        start_time = _now() - timedelta(hours=since_hours) if since_hours is not None else None
        return await self.repos.security_events.count_by_type(tenant_id, start_time=start_time)

    async def sweep_retention(self, tenant_id: str) -> int:
        cutoff = _now() - timedelta(days=self.settings.security_event_retention_days)
        return await self.repos.security_events.delete_older_than(tenant_id, cutoff)
