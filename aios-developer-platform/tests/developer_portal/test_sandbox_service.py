import uuid

import pytest

from developer_platform.config.settings import Settings
from developer_platform.core.exceptions import InvalidTransitionError, SandboxLimitExceededError, SandboxNotFoundError
from developer_platform.developer_portal.sandbox_service import SandboxService

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_provision_and_lifecycle(repos, db_session):
    tenant_id = _tid()
    service = SandboxService(repos)
    sandbox = await service.provision(tenant_id, "dev-1")
    await db_session.commit()
    assert sandbox.status == "provisioning"

    running = await service.mark_running(sandbox.id)
    await db_session.commit()
    assert running.status == "running"

    terminated = await service.terminate(sandbox.id)
    await db_session.commit()
    assert terminated.status == "terminated"
    assert terminated.terminated_at is not None


async def test_provision_enforces_concurrent_limit(repos, db_session):
    tenant_id = _tid()
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", secret_key="x" * 32, sandbox_max_concurrent_per_developer=2)
    service = SandboxService(repos, settings=settings)

    await service.provision(tenant_id, "dev-2")
    await service.provision(tenant_id, "dev-2")
    await db_session.commit()

    with pytest.raises(SandboxLimitExceededError):
        await service.provision(tenant_id, "dev-2")


async def test_terminated_sandbox_does_not_count_toward_limit(repos, db_session):
    tenant_id = _tid()
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", secret_key="x" * 32, sandbox_max_concurrent_per_developer=1)
    service = SandboxService(repos, settings=settings)

    first = await service.provision(tenant_id, "dev-3")
    await db_session.commit()
    await service.terminate(first.id)
    await db_session.commit()

    second = await service.provision(tenant_id, "dev-3")
    await db_session.commit()
    assert second.id != first.id


async def test_expire_from_running(repos, db_session):
    tenant_id = _tid()
    service = SandboxService(repos)
    sandbox = await service.provision(tenant_id, "dev-4")
    await db_session.commit()
    await service.mark_running(sandbox.id)
    await db_session.commit()

    expired = await service.expire(sandbox.id)
    await db_session.commit()
    assert expired.status == "expired"

    terminated = await service.terminate(sandbox.id)
    await db_session.commit()
    assert terminated.status == "terminated"


async def test_invalid_transition_raises(repos, db_session):
    tenant_id = _tid()
    service = SandboxService(repos)
    sandbox = await service.provision(tenant_id, "dev-5")
    await db_session.commit()
    with pytest.raises(InvalidTransitionError):
        await service.expire(sandbox.id)  # provisioning -> expired is not allowed


async def test_unknown_sandbox_raises(repos, db_session):
    service = SandboxService(repos)
    with pytest.raises(SandboxNotFoundError):
        await service.terminate("not-a-real-id")


async def test_sweep_expirations_transitions_overdue_running_sandboxes(repos, db_session):
    tenant_id = _tid()
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", secret_key="x" * 32, sandbox_ttl_minutes=-1)
    service = SandboxService(repos, settings=settings)

    sandbox = await service.provision(tenant_id, "dev-6")
    await db_session.commit()
    await service.mark_running(sandbox.id)
    await db_session.commit()

    swept = await service.sweep_expirations(tenant_id, "dev-6")
    await db_session.commit()
    assert len(swept) == 1
    assert swept[0].status == "expired"
