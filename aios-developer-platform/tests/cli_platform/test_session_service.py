import uuid

import pytest

from developer_platform.cli_platform.session_service import CliSessionService
from developer_platform.config.settings import Settings
from developer_platform.core.exceptions import CliNotAuthenticatedError, CliSessionExpiredError

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_start_and_verify_session(repos, db_session):
    tenant_id = _tid()
    service = CliSessionService(repos)

    result = await service.start_session(tenant_id, developer_id="dev-1")
    await db_session.commit()
    assert result.session.status == "active"

    verified = await service.verify_session(result.raw_token)
    assert verified.id == result.session.id
    assert verified.last_seen_at is not None


async def test_verify_unknown_token_raises(repos, db_session):
    service = CliSessionService(repos)
    with pytest.raises(CliNotAuthenticatedError):
        await service.verify_session("not-a-real-token")


async def test_revoke_then_verify_raises(repos, db_session):
    tenant_id = _tid()
    service = CliSessionService(repos)
    result = await service.start_session(tenant_id, developer_id="dev-2")
    await db_session.commit()

    await service.revoke_session(result.session.id)
    await db_session.commit()

    with pytest.raises(CliNotAuthenticatedError):
        await service.verify_session(result.raw_token)


async def test_expired_session_raises_and_transitions(repos, db_session):
    tenant_id = _tid()
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", secret_key="x" * 32, cli_token_ttl_minutes=-1)
    service = CliSessionService(repos, settings=settings)
    result = await service.start_session(tenant_id, developer_id="dev-3")
    await db_session.commit()

    with pytest.raises(CliSessionExpiredError):
        await service.verify_session(result.raw_token)
    await db_session.commit()

    listed = await service.list_for_developer(tenant_id, "dev-3")
    assert listed[0].status == "expired"


async def test_list_for_developer(repos, db_session):
    tenant_id = _tid()
    service = CliSessionService(repos)
    await service.start_session(tenant_id, developer_id="dev-4")
    await service.start_session(tenant_id, developer_id="dev-4")
    await db_session.commit()

    listed = await service.list_for_developer(tenant_id, "dev-4")
    assert len(listed) == 2
