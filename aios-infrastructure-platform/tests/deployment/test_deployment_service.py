"""Tests for Deployment Strategies: lifecycle transitions, rollback
from multiple states, auto-rollback on error-rate breach, canary step
advancement, blue-green cutover, and feature flags."""
from __future__ import annotations

import pytest

from infra_platform.config.settings import Settings
from infra_platform.core.exceptions import DeploymentError, DeploymentFailedError, NotFoundError, RollbackError, TrafficSplitError
from infra_platform.deployment.deployment_service import DeploymentService, FeatureFlagService

TENANT = "tenant-deploy"


@pytest.mark.asyncio
async def test_rolling_deployment_happy_path(repos):
    service = DeploymentService(repos)
    deployment = await service.create_deployment(TENANT, name="api-rollout", target_version="1.2.0", strategy="rolling")
    assert deployment.status == "pending"

    deployment = await service.start(TENANT, deployment.id)
    assert deployment.status == "in_progress"

    deployment = await service.succeed(TENANT, deployment.id)
    assert deployment.status == "succeeded"
    assert deployment.finished_at is not None

    events = await service.list_events(TENANT, deployment.id)
    assert [e.event_type for e in events] == ["started", "succeeded"]


@pytest.mark.asyncio
async def test_deployment_failure_raises_and_logs(repos):
    service = DeploymentService(repos)
    deployment = await service.create_deployment(TENANT, name="bad-rollout", target_version="2.0.0")
    await service.start(TENANT, deployment.id)

    with pytest.raises(DeploymentFailedError):
        await service.fail(TENANT, deployment.id, reason="health check failed")

    refreshed = await service._get(TENANT, deployment.id)
    assert refreshed.status == "failed"


@pytest.mark.asyncio
async def test_rollback_from_succeeded_and_pending_rejected(repos):
    service = DeploymentService(repos)
    deployment = await service.create_deployment(TENANT, name="rollback-test", target_version="3.0.0")

    with pytest.raises(RollbackError):
        await service.rollback(TENANT, deployment.id)  # pending cannot roll back

    await service.start(TENANT, deployment.id)
    await service.succeed(TENANT, deployment.id)
    deployment = await service.rollback(TENANT, deployment.id, reason="manual revert")
    assert deployment.status == "rolled_back"
    assert deployment.traffic_percentage == 0


@pytest.mark.asyncio
async def test_auto_rollback_on_error_rate_breach(repos):
    service = DeploymentService(repos, settings=Settings(rollback_on_error_rate_threshold=0.05))
    deployment = await service.create_deployment(TENANT, name="canary-rollout", target_version="4.0.0", strategy="canary")
    await service.start(TENANT, deployment.id)

    deployment, rolled_back = await service.check_error_rate_and_maybe_rollback(TENANT, deployment.id, error_rate=0.01)
    assert rolled_back is False
    assert deployment.status == "in_progress"

    deployment, rolled_back = await service.check_error_rate_and_maybe_rollback(TENANT, deployment.id, error_rate=0.20)
    assert rolled_back is True
    assert deployment.status == "rolled_back"


@pytest.mark.asyncio
async def test_canary_step_advancement_and_wrong_strategy(repos):
    service = DeploymentService(repos)
    canary = await service.create_deployment(TENANT, name="canary-only", target_version="5.0.0", strategy="canary")
    await service.start(TENANT, canary.id)

    canary = await service.advance_canary_step(TENANT, canary.id, step_percentage=25)
    assert canary.traffic_percentage == 25

    splits = await service.list_traffic_splits(TENANT, canary.id)
    weights = {s.variant: s.weight for s in splits}
    assert weights == {"canary": 25, "stable": 75}

    rolling = await service.create_deployment(TENANT, name="not-canary", target_version="5.0.1", strategy="rolling")
    with pytest.raises(TrafficSplitError):
        await service.advance_canary_step(TENANT, rolling.id, step_percentage=25)


@pytest.mark.asyncio
async def test_blue_green_cutover(repos):
    service = DeploymentService(repos)
    deployment = await service.create_deployment(TENANT, name="bg-rollout", target_version="6.0.0", strategy="blue_green")
    await service.start(TENANT, deployment.id)

    deployment = await service.blue_green_cutover(TENANT, deployment.id)
    assert deployment.traffic_percentage == 100

    splits = await service.list_traffic_splits(TENANT, deployment.id)
    weights = {s.variant: s.weight for s in splits}
    assert weights == {"green": 100, "blue": 0}


@pytest.mark.asyncio
async def test_unknown_strategy_rejected(repos):
    service = DeploymentService(repos)
    with pytest.raises(DeploymentError):
        await service.create_deployment(TENANT, name="bad-strategy", target_version="1.0.0", strategy="teleport")


@pytest.mark.asyncio
async def test_feature_flag_rollout_bucketing(repos):
    service = FeatureFlagService(repos)
    flag = await service.create_flag(TENANT, key="new-checkout", rollout_percentage=30)
    assert flag.is_enabled is False

    await service.enable(TENANT, "new-checkout")
    assert await service.is_enabled_for(TENANT, "new-checkout", bucket=10) is True
    assert await service.is_enabled_for(TENANT, "new-checkout", bucket=50) is False

    await service.set_rollout(TENANT, "new-checkout", percentage=100)
    assert await service.is_enabled_for(TENANT, "new-checkout", bucket=99) is True

    await service.disable(TENANT, "new-checkout")
    assert await service.is_enabled_for(TENANT, "new-checkout", bucket=10) is False

    with pytest.raises(DeploymentError):
        await service.create_flag(TENANT, key="new-checkout")


@pytest.mark.asyncio
async def test_deployment_not_found(repos):
    service = DeploymentService(repos)
    with pytest.raises(NotFoundError):
        await service.start(TENANT, "no-such-deployment")
