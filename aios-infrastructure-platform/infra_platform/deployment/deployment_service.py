"""Deployment strategies: a single guarded `Deployment` lifecycle
(pending -> in_progress -> succeeded/failed, with pause/resume for
canary bake windows and rollback reachable from any non-pending,
non-terminal state) parameterized by a `strategy` field (rolling,
blue-green, canary, shadow, recreate) rather than five separate state
machines. Traffic-split snapshots and an append-only event log ride
alongside every state change. Feature flags provide the
percentage-rollout primitive for gradual/targeted release outside the
deployment lifecycle entirely."""
from __future__ import annotations

from infra_platform.config.settings import Settings, get_settings
from infra_platform.core.exceptions import (
    DeploymentError,
    DeploymentFailedError,
    InvalidTransitionError,
    NotFoundError,
    RollbackError,
    TrafficSplitError,
)
from infra_platform.domain.entities import Deployment as DeploymentEntity
from infra_platform.domain.enums import DeploymentStatus, DeploymentStrategy
from infra_platform.models.deployment import DeploymentEventModel, DeploymentModel, FeatureFlagModel, TrafficSplitModel
from infra_platform.repositories.registry import RepositoryRegistry


def _to_entity(model: DeploymentModel) -> DeploymentEntity:
    return DeploymentEntity(id=model.id, status=DeploymentStatus(model.status))


class DeploymentService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def create_deployment(
        self, tenant_id: str, *, name: str, target_version: str, service_id: str | None = None,
        strategy: str = "rolling", previous_version: str | None = None,
    ) -> DeploymentModel:
        if strategy not in {s.value for s in DeploymentStrategy}:
            raise DeploymentError(f"Unknown deployment strategy '{strategy}'")
        deployment = DeploymentModel(
            tenant_id=tenant_id, service_id=service_id, name=name, strategy=strategy,
            status=DeploymentStatus.PENDING.value, target_version=target_version, previous_version=previous_version,
            traffic_percentage=0,
        )
        return await self.repos.deployments.add(deployment)

    async def _get(self, tenant_id: str, deployment_id: str) -> DeploymentModel:
        deployment = await self.repos.deployments.get(deployment_id)
        if deployment is None or deployment.tenant_id != tenant_id:
            raise NotFoundError(f"Deployment '{deployment_id}' not found")
        return deployment

    async def _log_event(self, tenant_id: str, deployment_id: str, *, event_type: str, message: str = "") -> None:
        await self.repos.deployment_events.add(
            DeploymentEventModel(tenant_id=tenant_id, deployment_id=deployment_id, event_type=event_type, message=message)
        )

    async def _transition(self, tenant_id: str, deployment_id: str, action: str, *, event_type: str, message: str = "") -> DeploymentModel:
        deployment = await self._get(tenant_id, deployment_id)
        entity = _to_entity(deployment)
        getattr(entity, action)()
        deployment.status = entity.status.value
        deployment.finished_at = entity.finished_at
        deployment = await self.repos.deployments.update(deployment)
        await self._log_event(tenant_id, deployment_id, event_type=event_type, message=message)
        return deployment

    async def start(self, tenant_id: str, deployment_id: str) -> DeploymentModel:
        return await self._transition(tenant_id, deployment_id, "start", event_type="started")

    async def pause(self, tenant_id: str, deployment_id: str, *, message: str = "") -> DeploymentModel:
        return await self._transition(tenant_id, deployment_id, "pause", event_type="paused", message=message)

    async def resume(self, tenant_id: str, deployment_id: str) -> DeploymentModel:
        return await self._transition(tenant_id, deployment_id, "resume", event_type="resumed")

    async def succeed(self, tenant_id: str, deployment_id: str) -> DeploymentModel:
        return await self._transition(tenant_id, deployment_id, "succeed", event_type="succeeded")

    async def fail(self, tenant_id: str, deployment_id: str, *, reason: str = "") -> DeploymentModel:
        await self._transition(tenant_id, deployment_id, "fail", event_type="failed", message=reason)
        raise DeploymentFailedError(f"Deployment '{deployment_id}' failed: {reason}" if reason else f"Deployment '{deployment_id}' failed")

    async def rollback(self, tenant_id: str, deployment_id: str, *, reason: str = "") -> DeploymentModel:
        deployment = await self._get(tenant_id, deployment_id)
        entity = _to_entity(deployment)
        try:
            entity.rollback()
        except InvalidTransitionError as exc:
            raise RollbackError(f"Deployment '{deployment_id}' cannot be rolled back from {deployment.status}") from exc
        deployment.status = entity.status.value
        deployment.finished_at = entity.finished_at
        deployment.traffic_percentage = 0
        deployment = await self.repos.deployments.update(deployment)
        await self._log_event(tenant_id, deployment_id, event_type="rolled_back", message=reason)
        return deployment

    async def check_error_rate_and_maybe_rollback(
        self, tenant_id: str, deployment_id: str, *, error_rate: float
    ) -> tuple[DeploymentModel, bool]:
        """Auto-rollback guard: if `error_rate` breaches
        `rollback_on_error_rate_threshold`, rolls the deployment back
        and returns `(deployment, True)`; otherwise a no-op returning
        `(deployment, False)`."""
        if error_rate > self.settings.rollback_on_error_rate_threshold:
            deployment = await self.rollback(
                tenant_id, deployment_id, reason=f"error rate {error_rate:.4f} exceeded threshold {self.settings.rollback_on_error_rate_threshold}"
            )
            return deployment, True
        deployment = await self._get(tenant_id, deployment_id)
        return deployment, False

    async def advance_canary_step(self, tenant_id: str, deployment_id: str, *, step_percentage: int) -> DeploymentModel:
        deployment = await self._get(tenant_id, deployment_id)
        if deployment.strategy != DeploymentStrategy.CANARY.value:
            raise TrafficSplitError(f"Deployment '{deployment_id}' is not a canary deployment (strategy={deployment.strategy})")
        if not (0 <= step_percentage <= 100):
            raise TrafficSplitError("step_percentage must be between 0 and 100")
        deployment.traffic_percentage = step_percentage
        deployment = await self.repos.deployments.update(deployment)
        await self.repos.traffic_splits.add(
            TrafficSplitModel(tenant_id=tenant_id, deployment_id=deployment_id, variant="canary", weight=step_percentage)
        )
        await self.repos.traffic_splits.add(
            TrafficSplitModel(tenant_id=tenant_id, deployment_id=deployment_id, variant="stable", weight=100 - step_percentage)
        )
        return deployment

    async def blue_green_cutover(self, tenant_id: str, deployment_id: str) -> DeploymentModel:
        deployment = await self._get(tenant_id, deployment_id)
        if deployment.strategy != DeploymentStrategy.BLUE_GREEN.value:
            raise TrafficSplitError(f"Deployment '{deployment_id}' is not a blue-green deployment (strategy={deployment.strategy})")
        deployment.traffic_percentage = 100
        deployment = await self.repos.deployments.update(deployment)
        await self.repos.traffic_splits.add(
            TrafficSplitModel(tenant_id=tenant_id, deployment_id=deployment_id, variant="green", weight=100)
        )
        await self.repos.traffic_splits.add(
            TrafficSplitModel(tenant_id=tenant_id, deployment_id=deployment_id, variant="blue", weight=0)
        )
        return deployment

    async def list_events(self, tenant_id: str, deployment_id: str) -> list[DeploymentEventModel]:
        return await self.repos.deployment_events.list_for_deployment(tenant_id, deployment_id)

    async def list_traffic_splits(self, tenant_id: str, deployment_id: str) -> list[TrafficSplitModel]:
        return await self.repos.traffic_splits.list_for_deployment(tenant_id, deployment_id)

    async def list_for_service(self, tenant_id: str, service_id: str) -> list[DeploymentModel]:
        return await self.repos.deployments.list_for_service(tenant_id, service_id)

    async def count_by_status(self, tenant_id: str) -> dict[str, int]:
        return await self.repos.deployments.count_by_status(tenant_id)


class FeatureFlagService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_flag(
        self, tenant_id: str, *, key: str, description: str | None = None, is_enabled: bool = False, rollout_percentage: int = 0
    ) -> FeatureFlagModel:
        existing = await self.repos.feature_flags.get_by_key(tenant_id, key)
        if existing is not None:
            raise DeploymentError(f"Feature flag '{key}' already exists")
        if not (0 <= rollout_percentage <= 100):
            raise DeploymentError("rollout_percentage must be between 0 and 100")
        flag = FeatureFlagModel(tenant_id=tenant_id, key=key, description=description, is_enabled=is_enabled, rollout_percentage=rollout_percentage)
        return await self.repos.feature_flags.add(flag)

    async def _get(self, tenant_id: str, key: str) -> FeatureFlagModel:
        flag = await self.repos.feature_flags.get_by_key(tenant_id, key)
        if flag is None:
            raise NotFoundError(f"Feature flag '{key}' not found")
        return flag

    async def set_rollout(self, tenant_id: str, key: str, *, percentage: int) -> FeatureFlagModel:
        if not (0 <= percentage <= 100):
            raise DeploymentError("rollout_percentage must be between 0 and 100")
        flag = await self._get(tenant_id, key)
        flag.rollout_percentage = percentage
        return await self.repos.feature_flags.update(flag)

    async def enable(self, tenant_id: str, key: str) -> FeatureFlagModel:
        flag = await self._get(tenant_id, key)
        flag.is_enabled = True
        return await self.repos.feature_flags.update(flag)

    async def disable(self, tenant_id: str, key: str) -> FeatureFlagModel:
        flag = await self._get(tenant_id, key)
        flag.is_enabled = False
        return await self.repos.feature_flags.update(flag)

    async def is_enabled_for(self, tenant_id: str, key: str, *, bucket: int) -> bool:
        """`bucket` is a caller-computed stable hash of the targeting
        key (e.g. user id) reduced to [0, 100); the flag is active for
        that bucket if the flag is enabled and the bucket falls under
        the rollout percentage."""
        flag = await self._get(tenant_id, key)
        return flag.is_enabled and bucket < flag.rollout_percentage

    async def list_for_tenant(self, tenant_id: str) -> list[FeatureFlagModel]:
        return await self.repos.feature_flags.list_for_tenant(tenant_id)
