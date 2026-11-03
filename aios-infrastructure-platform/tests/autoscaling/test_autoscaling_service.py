"""Tests for generic autoscaling policies: capacity clamping,
no-op when desired equals current, cooldown enforcement (asymmetric
up/down), and disabled-policy/cost-aware gating."""
from __future__ import annotations

import asyncio

import pytest

from infra_platform.autoscaling.autoscaling_service import ScalingPolicyService
from infra_platform.config.settings import Settings
from infra_platform.core.exceptions import AutoscalingError, NotFoundError, ScalingPolicyError

TENANT = "tenant-autoscaling"


@pytest.mark.asyncio
async def test_create_policy_rejects_unknown_type_and_bad_bounds(repos):
    service = ScalingPolicyService(repos)
    with pytest.raises(ScalingPolicyError):
        await service.create_policy(TENANT, resource_type="inference_service", resource_id="svc-1", policy_type="warp_speed")

    with pytest.raises(ScalingPolicyError):
        await service.create_policy(TENANT, resource_type="inference_service", resource_id="svc-1", policy_type="horizontal", min_capacity=10, max_capacity=2)


@pytest.mark.asyncio
async def test_evaluate_scale_clamps_to_bounds(repos):
    service = ScalingPolicyService(repos, settings=Settings(scale_up_cooldown_seconds=0, scale_down_cooldown_seconds=0))
    policy = await service.create_policy(
        TENANT, resource_type="node_pool", resource_id="pool-1", policy_type="horizontal", min_capacity=2, max_capacity=8
    )

    event = await service.evaluate_scale(TENANT, policy.id, current_capacity=2, desired_capacity=20)
    assert event.to_capacity == 8  # clamped to max
    assert event.direction == "up"


@pytest.mark.asyncio
async def test_evaluate_scale_noop_when_equal(repos):
    service = ScalingPolicyService(repos, settings=Settings(scale_up_cooldown_seconds=0, scale_down_cooldown_seconds=0))
    policy = await service.create_policy(TENANT, resource_type="node_pool", resource_id="pool-2", policy_type="horizontal")
    event = await service.evaluate_scale(TENANT, policy.id, current_capacity=3, desired_capacity=3)
    assert event is None


@pytest.mark.asyncio
async def test_cooldown_blocks_rapid_rescale(repos):
    service = ScalingPolicyService(repos, settings=Settings(scale_up_cooldown_seconds=60, scale_down_cooldown_seconds=60))
    policy = await service.create_policy(TENANT, resource_type="node_pool", resource_id="pool-3", policy_type="horizontal", min_capacity=1, max_capacity=20)

    await service.evaluate_scale(TENANT, policy.id, current_capacity=2, desired_capacity=4)
    with pytest.raises(AutoscalingError):
        await service.evaluate_scale(TENANT, policy.id, current_capacity=4, desired_capacity=6)


@pytest.mark.asyncio
async def test_cooldown_expires_after_wait(repos):
    service = ScalingPolicyService(repos, settings=Settings(scale_up_cooldown_seconds=1, scale_down_cooldown_seconds=1))
    policy = await service.create_policy(TENANT, resource_type="node_pool", resource_id="pool-4", policy_type="horizontal", min_capacity=1, max_capacity=20)

    await service.evaluate_scale(TENANT, policy.id, current_capacity=2, desired_capacity=4)
    await asyncio.sleep(1.1)
    event = await service.evaluate_scale(TENANT, policy.id, current_capacity=4, desired_capacity=6)
    assert event.to_capacity == 6


@pytest.mark.asyncio
async def test_disabled_policy_rejects_scale(repos):
    service = ScalingPolicyService(repos, settings=Settings(scale_up_cooldown_seconds=0, scale_down_cooldown_seconds=0))
    policy = await service.create_policy(TENANT, resource_type="cluster", resource_id="cluster-1", policy_type="cluster")
    await service.set_enabled(TENANT, policy.id, enabled=False)

    with pytest.raises(AutoscalingError):
        await service.evaluate_scale(TENANT, policy.id, current_capacity=2, desired_capacity=4)


@pytest.mark.asyncio
async def test_cost_aware_disabled_setting_blocks_creation(repos):
    service = ScalingPolicyService(repos, settings=Settings(cost_aware_scaling_enabled=False))
    with pytest.raises(ScalingPolicyError):
        await service.create_policy(TENANT, resource_type="node_pool", resource_id="pool-5", policy_type="cost_aware")


@pytest.mark.asyncio
async def test_policy_not_found(repos):
    service = ScalingPolicyService(repos)
    with pytest.raises(NotFoundError):
        await service.evaluate_scale(TENANT, "no-such-policy", current_capacity=1, desired_capacity=2)
