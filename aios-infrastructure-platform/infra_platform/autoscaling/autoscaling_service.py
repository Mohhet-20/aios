"""Generic autoscaling: `ScalingPolicyModel` is polymorphic over
`resource_type`/`resource_id` and `policy_type` (horizontal, vertical,
cluster, GPU, queue-based, predictive, cost-aware) — one table rather
than seven near-identical ones, the same pattern used elsewhere in
this platform (`K8sResourceModel`, the Security Platform's
`RiskScoreModel`). `evaluate_scale` clamps the desired capacity to the
policy's bounds and enforces asymmetric up/down cooldowns against the
policy's own scaling-event history — scaling up defends availability
so it cools down fast, scaling down defends against flapping so it
cools down slow, mirroring the platform's `scale_up_cooldown_seconds`
< `scale_down_cooldown_seconds` default."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import timezone

from infra_platform.config.settings import Settings, get_settings
from infra_platform.core.exceptions import AutoscalingError, NotFoundError, ScalingPolicyError
from infra_platform.domain.enums import ScalingDirection, ScalingPolicyType
from infra_platform.models.autoscaling import ScalingEventModel, ScalingPolicyModel
from infra_platform.repositories.registry import RepositoryRegistry
from infra_platform.clock import utc_now


class ScalingPolicyService:
    """`evaluate_scale`'s cooldown-check-then-record-event sequence
    spans multiple statements; two concurrent evaluations for the same
    policy could otherwise both read the same "last event" and both
    conclude the cooldown has expired, firing two scaling events where
    only one should have been allowed through. Serialized per
    `policy_id` with an in-process `asyncio.Lock`, the same commit-
    spanning-lock pattern used throughout the AIOS build (e.g. the
    Security Platform's `SecretService.rotate_secret`)."""

    _scale_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def create_policy(
        self, tenant_id: str, *, resource_type: str, resource_id: str, policy_type: str,
        min_capacity: int = 1, max_capacity: int = 10, target_metric: str | None = None, target_value: float | None = None,
    ) -> ScalingPolicyModel:
        if policy_type not in {p.value for p in ScalingPolicyType}:
            raise ScalingPolicyError(f"Unknown scaling policy type '{policy_type}'")
        if min_capacity > max_capacity:
            raise ScalingPolicyError("min_capacity cannot exceed max_capacity")
        if self.settings.cost_aware_scaling_enabled is False and policy_type == ScalingPolicyType.COST_AWARE.value:
            raise ScalingPolicyError("cost-aware scaling is disabled for this deployment")
        policy = ScalingPolicyModel(
            tenant_id=tenant_id, resource_type=resource_type, resource_id=resource_id, policy_type=policy_type,
            min_capacity=min_capacity, max_capacity=max_capacity, target_metric=target_metric, target_value=target_value,
            is_enabled=True,
        )
        return await self.repos.scaling_policies.add(policy)

    async def _get(self, tenant_id: str, policy_id: str) -> ScalingPolicyModel:
        policy = await self.repos.scaling_policies.get(policy_id)
        if policy is None or policy.tenant_id != tenant_id:
            raise NotFoundError(f"ScalingPolicy '{policy_id}' not found")
        return policy

    async def set_enabled(self, tenant_id: str, policy_id: str, *, enabled: bool) -> ScalingPolicyModel:
        policy = await self._get(tenant_id, policy_id)
        policy.is_enabled = enabled
        return await self.repos.scaling_policies.update(policy)

    async def evaluate_scale(
        self, tenant_id: str, policy_id: str, *, current_capacity: int, desired_capacity: int, reason: str | None = None
    ) -> ScalingEventModel | None:
        async with self._scale_locks[policy_id]:
            policy = await self._get(tenant_id, policy_id)
            if not policy.is_enabled:
                raise AutoscalingError(f"ScalingPolicy '{policy_id}' is disabled")

            clamped = max(policy.min_capacity, min(policy.max_capacity, desired_capacity))
            if clamped == current_capacity:
                return None

            direction = ScalingDirection.UP.value if clamped > current_capacity else ScalingDirection.DOWN.value
            cooldown = (
                self.settings.scale_up_cooldown_seconds if direction == ScalingDirection.UP.value
                else self.settings.scale_down_cooldown_seconds
            )

            recent = await self.repos.scaling_events.list_for_policy(tenant_id, policy_id, limit=1)
            if recent:
                last_occurred = recent[0].occurred_at
                if last_occurred.tzinfo is None:
                    last_occurred = last_occurred.replace(tzinfo=timezone.utc)
                elapsed = (utc_now() - last_occurred).total_seconds()
                if elapsed < cooldown:
                    raise AutoscalingError(
                        f"ScalingPolicy '{policy_id}' is cooling down ({cooldown - elapsed:.0f}s remaining before next {direction}-scale)"
                    )

            event = ScalingEventModel(
                tenant_id=tenant_id, policy_id=policy_id, direction=direction,
                from_capacity=current_capacity, to_capacity=clamped, reason=reason,
            )
            result = await self.repos.scaling_events.add(event)
            await self.repos.session.commit()
            return result

    async def list_for_resource(self, tenant_id: str, resource_type: str, resource_id: str) -> list[ScalingPolicyModel]:
        return await self.repos.scaling_policies.list_for_resource(tenant_id, resource_type, resource_id)

    async def list_enabled_for_resource(self, tenant_id: str, resource_type: str, resource_id: str) -> list[ScalingPolicyModel]:
        return await self.repos.scaling_policies.list_enabled_for_resource(tenant_id, resource_type, resource_id)

    async def list_events(self, tenant_id: str, policy_id: str) -> list[ScalingEventModel]:
        return await self.repos.scaling_events.list_for_policy(tenant_id, policy_id)
