import pytest

from release_platform.core.exceptions import NotFoundError, UnsupportedEnvironmentTypeError
from release_platform.environments.environment_service import EnvironmentService

pytestmark = pytest.mark.asyncio

TENANT = "t-environments"


async def test_register_environment_rejects_unsupported_type(repos):
    svc = EnvironmentService(repos)
    with pytest.raises(UnsupportedEnvironmentTypeError):
        await svc.register_environment(TENANT, name="prod-mars", environment_type="mars_colony")


async def test_get_or_404_raises_for_missing(repos):
    svc = EnvironmentService(repos)
    with pytest.raises(NotFoundError):
        await svc.get_or_404(TENANT, "nonexistent-id")


async def test_register_environment_is_idempotent(repos):
    svc = EnvironmentService(repos)
    env1 = await svc.register_environment(TENANT, name="prod-us-east", environment_type="production", region="us-east-1")
    env2 = await svc.register_environment(TENANT, name="prod-us-east", environment_type="production", region="us-east-1")
    assert env1.id == env2.id


async def test_activate_deactivate(repos):
    svc = EnvironmentService(repos)
    env = await svc.register_environment(TENANT, name="staging-1", environment_type="staging")
    assert env.is_active is True
    env = await svc.deactivate(TENANT, env.id)
    assert env.is_active is False
    env = await svc.activate(TENANT, env.id)
    assert env.is_active is True


async def test_list_environments_filters_by_type(repos):
    svc = EnvironmentService(repos)
    await svc.register_environment(TENANT, name="qa-1", environment_type="qa")
    await svc.register_environment(TENANT, name="sandbox-1", environment_type="sandbox")
    qa_only = await svc.list_environments(TENANT, environment_type="qa")
    assert all(e.environment_type == "qa" for e in qa_only)
    assert len(qa_only) == 1
