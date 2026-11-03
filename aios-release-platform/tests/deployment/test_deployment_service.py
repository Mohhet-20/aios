import pytest

from release_platform.core.exceptions import InvalidTransitionError, NotFoundError, UnsupportedDeploymentTargetError
from release_platform.deployment.deployment_service import DeploymentService

pytestmark = pytest.mark.asyncio

TENANT = "t-deployment"


async def test_create_deployment_rejects_unsupported_target(repos):
    svc = DeploymentService(repos)
    with pytest.raises(UnsupportedDeploymentTargetError):
        await svc.create_deployment(TENANT, release_id="r1", environment_id="e1", target_type="lunar_base")


async def test_get_or_404_raises_for_missing(repos):
    svc = DeploymentService(repos)
    with pytest.raises(NotFoundError):
        await svc.get_or_404(TENANT, "nonexistent-id")


async def test_full_success_lifecycle(repos):
    svc = DeploymentService(repos)
    deployment = await svc.create_deployment(TENANT, release_id="r1", environment_id="e1", target_type="cloud")
    assert deployment.status == "queued"

    deployment = await svc.start(TENANT, deployment.id)
    assert deployment.status == "in_progress"
    assert deployment.started_at is not None

    deployment = await svc.succeed(TENANT, deployment.id)
    assert deployment.status == "succeeded"
    assert deployment.finished_at is not None

    deployment = await svc.mark_rolled_back(TENANT, deployment.id)
    assert deployment.status == "rolled_back"


async def test_failure_path_records_reason(repos):
    svc = DeploymentService(repos)
    deployment = await svc.create_deployment(TENANT, release_id="r2", environment_id="e1", target_type="multi_region")
    deployment = await svc.start(TENANT, deployment.id)
    deployment = await svc.fail(TENANT, deployment.id, reason="health check failed")
    assert deployment.status == "failed"
    assert deployment.failure_reason == "health check failed"


async def test_cannot_succeed_before_starting(repos):
    svc = DeploymentService(repos)
    deployment = await svc.create_deployment(TENANT, release_id="r3", environment_id="e1", target_type="edge")
    with pytest.raises(InvalidTransitionError):
        await svc.succeed(TENANT, deployment.id)


async def test_failed_deployment_is_terminal(repos):
    svc = DeploymentService(repos)
    deployment = await svc.create_deployment(TENANT, release_id="r4", environment_id="e1", target_type="on_prem")
    deployment = await svc.start(TENANT, deployment.id)
    deployment = await svc.fail(TENANT, deployment.id, reason="oops")
    with pytest.raises(InvalidTransitionError):
        await svc.mark_rolled_back(TENANT, deployment.id)


async def test_list_deployments_filters_by_status(repos):
    svc = DeploymentService(repos)
    d1 = await svc.create_deployment(TENANT, release_id="r5", environment_id="e2", target_type="hybrid")
    await svc.create_deployment(TENANT, release_id="r6", environment_id="e2", target_type="hybrid")
    await svc.start(TENANT, d1.id)
    in_progress = await svc.list_deployments(TENANT, environment_id="e2", status="in_progress")
    assert len(in_progress) == 1
