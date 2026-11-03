"""Rollout Engine: progressive rollout execution across the 10
declared strategies (blue-green, canary, rolling, shadow, progressive,
percentage, region, organization, tenant, feature), attached to a
deployment and guarded through the ephemeral `Rollout` domain entity's
planned -> in_progress -> paused/completed/aborted lifecycle.

Deliberately does not cross-validate `deployment_id` against a real
deployment row, the same loose-coupling choice `DeploymentService`
makes for `release_id`/`environment_id` — see that module's docstring
for the rationale."""
from __future__ import annotations

from release_platform.config.settings import get_settings
from release_platform.core.exceptions import RolloutNotFoundError, UnsupportedRolloutStrategyError
from release_platform.domain.entities import Rollout
from release_platform.domain.enums import RolloutStatus
from release_platform.models.rollout import RolloutModel
from release_platform.repositories.registry import RepositoryRegistry


class RolloutService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, rollout_id: str) -> RolloutModel:
        rollout = await self.repos.rollouts.get_or_404(rollout_id)
        if rollout.tenant_id != tenant_id:
            raise RolloutNotFoundError(f"Rollout '{rollout_id}' not found for tenant '{tenant_id}'")
        return rollout

    async def plan_rollout(
        self, tenant_id: str, *, deployment_id: str, strategy: str, target_ref: str | None = None
    ) -> RolloutModel:
        if strategy not in self.settings.rollout_strategies:
            raise UnsupportedRolloutStrategyError(f"Unsupported rollout strategy '{strategy}'")
        rollout = RolloutModel(
            tenant_id=tenant_id, deployment_id=deployment_id, strategy=strategy,
            status=RolloutStatus.PLANNED.value, target_ref=target_ref, current_step_pct=0.0,
        )
        return await self.repos.rollouts.add(rollout)

    def _to_entity(self, rollout: RolloutModel) -> Rollout:
        return Rollout(
            id=rollout.id, tenant_id=rollout.tenant_id, deployment_id=rollout.deployment_id, strategy=rollout.strategy,
            status=RolloutStatus(rollout.status), current_step_pct=rollout.current_step_pct,
        )

    async def start(self, tenant_id: str, rollout_id: str) -> RolloutModel:
        rollout = await self.get_or_404(tenant_id, rollout_id)
        entity = self._to_entity(rollout)
        entity.start()
        rollout.status = entity.status.value
        rollout.started_at = entity.started_at
        return rollout

    async def pause(self, tenant_id: str, rollout_id: str) -> RolloutModel:
        rollout = await self.get_or_404(tenant_id, rollout_id)
        entity = self._to_entity(rollout)
        entity.pause()
        rollout.status = entity.status.value
        return rollout

    async def resume(self, tenant_id: str, rollout_id: str) -> RolloutModel:
        rollout = await self.get_or_404(tenant_id, rollout_id)
        entity = self._to_entity(rollout)
        entity.resume()
        rollout.status = entity.status.value
        return rollout

    async def advance(self, tenant_id: str, rollout_id: str, *, step_pct: float) -> RolloutModel:
        rollout = await self.get_or_404(tenant_id, rollout_id)
        entity = self._to_entity(rollout)
        entity.advance(step_pct=step_pct)
        rollout.current_step_pct = entity.current_step_pct
        return rollout

    async def advance_by_default_step(self, tenant_id: str, rollout_id: str) -> RolloutModel:
        rollout = await self.get_or_404(tenant_id, rollout_id)
        target = min(rollout.current_step_pct + self.settings.rollout_default_step_pct, 100.0)
        return await self.advance(tenant_id, rollout_id, step_pct=target)

    async def complete(self, tenant_id: str, rollout_id: str) -> RolloutModel:
        rollout = await self.get_or_404(tenant_id, rollout_id)
        entity = self._to_entity(rollout)
        entity.complete()
        rollout.status = entity.status.value
        rollout.current_step_pct = entity.current_step_pct
        rollout.completed_at = entity.completed_at
        return rollout

    async def abort(self, tenant_id: str, rollout_id: str) -> RolloutModel:
        rollout = await self.get_or_404(tenant_id, rollout_id)
        entity = self._to_entity(rollout)
        entity.abort()
        rollout.status = entity.status.value
        return rollout

    async def list_for_deployment(self, tenant_id: str, deployment_id: str) -> list[RolloutModel]:
        return await self.repos.rollouts.list_for_deployment(tenant_id, deployment_id)
