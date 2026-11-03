import pytest

from release_platform.core.exceptions import InvalidTransitionError, NotFoundError, UnsupportedRollbackTypeError
from release_platform.rollback.rollback_service import RollbackService

pytestmark = pytest.mark.asyncio

TENANT = "t-rollback"


async def test_initiate_rollback_rejects_unsupported_type(repos):
    svc = RollbackService(repos)
    with pytest.raises(UnsupportedRollbackTypeError):
        await svc.initiate_rollback(TENANT, deployment_id="d1", rollback_type="time_travel")


async def test_get_or_404_raises_for_missing(repos):
    svc = RollbackService(repos)
    with pytest.raises(NotFoundError):
        await svc.get_or_404(TENANT, "nonexistent-id")


async def test_full_success_lifecycle(repos):
    svc = RollbackService(repos)
    rollback = await svc.initiate_rollback(TENANT, deployment_id="d2", rollback_type="automatic", reason="failed health check")
    assert rollback.status == "queued"

    rollback = await svc.start(TENANT, rollback.id)
    assert rollback.status == "in_progress"
    assert rollback.started_at is not None

    rollback = await svc.complete(TENANT, rollback.id)
    assert rollback.status == "completed"
    assert rollback.completed_at is not None


async def test_failure_path(repos):
    svc = RollbackService(repos)
    rollback = await svc.initiate_rollback(TENANT, deployment_id="d3", rollback_type="database")
    rollback = await svc.start(TENANT, rollback.id)
    rollback = await svc.fail(TENANT, rollback.id)
    assert rollback.status == "failed"


async def test_cannot_complete_before_starting(repos):
    svc = RollbackService(repos)
    rollback = await svc.initiate_rollback(TENANT, deployment_id="d4", rollback_type="configuration")
    with pytest.raises(InvalidTransitionError):
        await svc.complete(TENANT, rollback.id)


async def test_completed_is_terminal(repos):
    svc = RollbackService(repos)
    rollback = await svc.initiate_rollback(TENANT, deployment_id="d5", rollback_type="feature")
    rollback = await svc.start(TENANT, rollback.id)
    rollback = await svc.complete(TENANT, rollback.id)
    with pytest.raises(InvalidTransitionError):
        await svc.fail(TENANT, rollback.id)


async def test_list_for_deployment(repos):
    svc = RollbackService(repos)
    await svc.initiate_rollback(TENANT, deployment_id="d6", rollback_type="model")
    await svc.initiate_rollback(TENANT, deployment_id="d6", rollback_type="infrastructure")
    rollbacks = await svc.list_for_deployment(TENANT, "d6")
    assert len(rollbacks) == 2
