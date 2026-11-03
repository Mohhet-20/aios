import pytest

from release_platform.core.exceptions import InvalidTransitionError, NotFoundError, UnsupportedRolloutStrategyError
from release_platform.rollouts.rollout_service import RolloutService

pytestmark = pytest.mark.asyncio

TENANT = "t-rollouts"


async def test_plan_rollout_rejects_unsupported_strategy(repos):
    svc = RolloutService(repos)
    with pytest.raises(UnsupportedRolloutStrategyError):
        await svc.plan_rollout(TENANT, deployment_id="d1", strategy="teleportation")


async def test_get_or_404_raises_for_missing(repos):
    svc = RolloutService(repos)
    with pytest.raises(NotFoundError):
        await svc.get_or_404(TENANT, "nonexistent-id")


async def test_full_rollout_lifecycle(repos):
    svc = RolloutService(repos)
    rollout = await svc.plan_rollout(TENANT, deployment_id="d1", strategy="canary")
    assert rollout.status == "planned"

    rollout = await svc.start(TENANT, rollout.id)
    assert rollout.status == "in_progress"
    assert rollout.started_at is not None

    rollout = await svc.advance(TENANT, rollout.id, step_pct=25.0)
    assert rollout.current_step_pct == 25.0

    rollout = await svc.pause(TENANT, rollout.id)
    assert rollout.status == "paused"

    rollout = await svc.resume(TENANT, rollout.id)
    assert rollout.status == "in_progress"

    rollout = await svc.complete(TENANT, rollout.id)
    assert rollout.status == "completed"
    assert rollout.current_step_pct == 100.0
    assert rollout.completed_at is not None


async def test_advance_by_default_step(repos):
    svc = RolloutService(repos)
    rollout = await svc.plan_rollout(TENANT, deployment_id="d2", strategy="percentage")
    await svc.start(TENANT, rollout.id)
    rollout = await svc.advance_by_default_step(TENANT, rollout.id)
    assert rollout.current_step_pct == 10.0
    rollout = await svc.advance_by_default_step(TENANT, rollout.id)
    assert rollout.current_step_pct == 20.0


async def test_cannot_advance_when_not_in_progress(repos):
    svc = RolloutService(repos)
    rollout = await svc.plan_rollout(TENANT, deployment_id="d3", strategy="rolling")
    with pytest.raises(InvalidTransitionError):
        await svc.advance(TENANT, rollout.id, step_pct=10.0)


async def test_abort_from_planned(repos):
    svc = RolloutService(repos)
    rollout = await svc.plan_rollout(TENANT, deployment_id="d4", strategy="blue_green")
    rollout = await svc.abort(TENANT, rollout.id)
    assert rollout.status == "aborted"


async def test_completed_rollout_is_terminal(repos):
    svc = RolloutService(repos)
    rollout = await svc.plan_rollout(TENANT, deployment_id="d5", strategy="shadow")
    await svc.start(TENANT, rollout.id)
    rollout = await svc.complete(TENANT, rollout.id)
    with pytest.raises(InvalidTransitionError):
        await svc.abort(TENANT, rollout.id)


async def test_list_for_deployment(repos):
    svc = RolloutService(repos)
    await svc.plan_rollout(TENANT, deployment_id="d6", strategy="region")
    await svc.plan_rollout(TENANT, deployment_id="d6", strategy="tenant")
    rollouts = await svc.list_for_deployment(TENANT, "d6")
    assert len(rollouts) == 2
