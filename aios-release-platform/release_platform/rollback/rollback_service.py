"""Rollback Engine: one row per rollback action taken against a
deployment, across the 8 declared rollback types (automatic, manual,
partial, database, configuration, feature, model, infrastructure),
guarded by an inline `_ROLLBACK_TRANSITIONS` dict (queued ->
in_progress -> completed/failed) — a "simple status field" resource in
the same sense as `UpdateJobService`. Deliberately does not itself
call `DeploymentService.mark_rolled_back` — the two are kept decoupled
so a caller can choose to record a rollback attempt without forcing a
deployment's own status to change (e.g. a partial/configuration
rollback that doesn't roll the whole deployment back), the same
loose-coupling rationale documented in `DeploymentService`."""
from __future__ import annotations


from release_platform.config.settings import get_settings
from release_platform.core.exceptions import InvalidTransitionError, RollbackNotFoundError, UnsupportedRollbackTypeError
from release_platform.models.rollback import RollbackModel
from release_platform.repositories.registry import RepositoryRegistry
from release_platform.clock import utc_now

_ROLLBACK_TRANSITIONS: dict[str, set[str]] = {
    "queued": {"in_progress"},
    "in_progress": {"completed", "failed"},
    "completed": set(),
    "failed": set(),
}


class RollbackService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, rollback_id: str) -> RollbackModel:
        rollback = await self.repos.rollbacks.get_or_404(rollback_id)
        if rollback.tenant_id != tenant_id:
            raise RollbackNotFoundError(f"Rollback '{rollback_id}' not found for tenant '{tenant_id}'")
        return rollback

    async def initiate_rollback(
        self, tenant_id: str, *, deployment_id: str, rollback_type: str, reason: str = "", initiated_by: str | None = None
    ) -> RollbackModel:
        if rollback_type not in self.settings.rollback_types:
            raise UnsupportedRollbackTypeError(f"Unsupported rollback type '{rollback_type}'")
        rollback = RollbackModel(
            tenant_id=tenant_id, deployment_id=deployment_id, rollback_type=rollback_type,
            status="queued", reason=reason, initiated_by=initiated_by,
        )
        return await self.repos.rollbacks.add(rollback)

    async def _transition(self, tenant_id: str, rollback_id: str, target: str) -> RollbackModel:
        rollback = await self.get_or_404(tenant_id, rollback_id)
        if target not in _ROLLBACK_TRANSITIONS.get(rollback.status, set()):
            raise InvalidTransitionError(f"Cannot transition rollback from '{rollback.status}' to '{target}'")
        rollback.status = target
        return rollback

    async def start(self, tenant_id: str, rollback_id: str) -> RollbackModel:
        rollback = await self._transition(tenant_id, rollback_id, "in_progress")
        rollback.started_at = utc_now()
        return rollback

    async def complete(self, tenant_id: str, rollback_id: str) -> RollbackModel:
        rollback = await self._transition(tenant_id, rollback_id, "completed")
        rollback.completed_at = utc_now()
        return rollback

    async def fail(self, tenant_id: str, rollback_id: str) -> RollbackModel:
        return await self._transition(tenant_id, rollback_id, "failed")

    async def list_for_deployment(self, tenant_id: str, deployment_id: str) -> list[RollbackModel]:
        return await self.repos.rollbacks.list_for_deployment(tenant_id, deployment_id)
