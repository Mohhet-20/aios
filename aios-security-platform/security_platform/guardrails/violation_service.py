"""Lifecycle management for guardrail violations: open -> acknowledged
-> resolved. Kept separate from GuardrailService (which only ever
creates violations as a side effect of evaluation) since acknowledgment
and resolution are actions taken later by a human reviewer, not part
of the evaluation flow itself."""
from __future__ import annotations

from security_platform.core.exceptions import InvalidTransitionError, NotFoundError
from security_platform.database.base import utcnow
from security_platform.domain.enums import ViolationStatus
from security_platform.models.guardrails import GuardrailViolationModel
from security_platform.repositories.registry import RepositoryRegistry

_ALLOWED_TRANSITIONS = {
    ViolationStatus.OPEN.value: {ViolationStatus.ACKNOWLEDGED.value, ViolationStatus.RESOLVED.value},
    ViolationStatus.ACKNOWLEDGED.value: {ViolationStatus.RESOLVED.value},
    ViolationStatus.RESOLVED.value: set(),
}


class GuardrailViolationService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def _get_scoped(self, tenant_id: str, violation_id: str) -> GuardrailViolationModel:
        violation = await self.repos.guardrail_violations.get(violation_id)
        if violation is None or violation.tenant_id != tenant_id:
            raise NotFoundError(f"GuardrailViolation '{violation_id}' not found")
        return violation

    async def _transition(self, tenant_id: str, violation_id: str, target: str, *, resolution_notes: str | None = None) -> GuardrailViolationModel:
        violation = await self._get_scoped(tenant_id, violation_id)
        if target not in _ALLOWED_TRANSITIONS.get(violation.status, set()):
            raise InvalidTransitionError(f"Cannot transition guardrail violation from '{violation.status}' to '{target}'")
        violation.status = target
        if target == ViolationStatus.RESOLVED.value:
            violation.resolved_at = utcnow()
            if resolution_notes is not None:
                violation.resolution_notes = resolution_notes
        return await self.repos.guardrail_violations.update(violation)

    async def acknowledge(self, tenant_id: str, violation_id: str) -> GuardrailViolationModel:
        return await self._transition(tenant_id, violation_id, ViolationStatus.ACKNOWLEDGED.value)

    async def resolve(self, tenant_id: str, violation_id: str, *, resolution_notes: str | None = None) -> GuardrailViolationModel:
        return await self._transition(tenant_id, violation_id, ViolationStatus.RESOLVED.value, resolution_notes=resolution_notes)

    async def list_open(self, tenant_id: str, *, limit: int = 200) -> list[GuardrailViolationModel]:
        return await self.repos.guardrail_violations.list_by_status(tenant_id, ViolationStatus.OPEN.value, limit=limit)
