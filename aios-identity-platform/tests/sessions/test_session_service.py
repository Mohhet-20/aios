import pytest

from identity_platform.core.exceptions import ConcurrentSessionLimitExceededError, SessionRevokedError
from identity_platform.domain.enums import UserStatus
from identity_platform.models.user import UserModel
from identity_platform.sessions.session_service import SessionService

pytestmark = pytest.mark.asyncio


async def _make_user(repos, db_session, email: str):
    user = UserModel(email=email, status=UserStatus.ACTIVE.value)
    await repos.users.add(user)
    await db_session.commit()
    return user


async def test_create_session_issues_access_and_refresh_tokens(repos, db_session):
    user = await _make_user(repos, db_session, "session-create@example.com")
    service = SessionService(repos)

    result = await service.create_session(user.id, ip_address="10.0.0.1", user_agent="pytest")
    await db_session.commit()

    assert result.session.status == "active"
    assert result.access_token
    assert result.raw_refresh_token

    payload = service.jwt_service.decode_access_token(result.access_token)
    assert payload["sub"] == user.id
    assert payload["sid"] == result.session.id


async def test_refresh_rotates_token_and_invalidates_old_one(repos, db_session):
    user = await _make_user(repos, db_session, "session-refresh@example.com")
    service = SessionService(repos)
    issued = await service.create_session(user.id)
    await db_session.commit()

    refreshed = await service.refresh(issued.raw_refresh_token)
    await db_session.commit()

    assert refreshed.session.id == issued.session.id
    assert refreshed.raw_refresh_token != issued.raw_refresh_token

    with pytest.raises(SessionRevokedError):
        await service.refresh(issued.raw_refresh_token)


async def test_revoke_session_prevents_further_refresh(repos, db_session):
    user = await _make_user(repos, db_session, "session-revoke@example.com")
    service = SessionService(repos)
    issued = await service.create_session(user.id)
    await db_session.commit()

    await service.revoke_session(issued.session.id, reason="manual_test")
    await db_session.commit()

    with pytest.raises(SessionRevokedError):
        await service.refresh(issued.raw_refresh_token)


async def test_revoke_all_for_user(repos, db_session):
    user = await _make_user(repos, db_session, "session-revoke-all@example.com")
    service = SessionService(repos)
    await service.create_session(user.id)
    await service.create_session(user.id)
    await db_session.commit()

    active_before = await service.list_active_for_user(user.id)
    assert len(active_before) == 2

    revoked_count = await service.revoke_all_for_user(user.id)
    await db_session.commit()
    assert revoked_count == 2

    active_after = await service.list_active_for_user(user.id)
    assert len(active_after) == 0


async def test_concurrent_session_limit_evicts_oldest_by_default(repos, db_session):
    from identity_platform.config.settings import Settings

    user = await _make_user(repos, db_session, "session-limit@example.com")
    settings = Settings(secret_key="x" * 32, max_concurrent_sessions_per_user=2)
    service = SessionService(repos, settings=settings)

    first = await service.create_session(user.id)
    await db_session.commit()
    await service.create_session(user.id)
    await db_session.commit()
    third = await service.create_session(user.id)
    await db_session.commit()

    active = await service.list_active_for_user(user.id)
    assert len(active) == 2
    assert third.session.id in {s.id for s in active}
    assert first.session.id not in {s.id for s in active}


async def test_concurrent_session_limit_raises_when_eviction_disabled(repos, db_session):
    from identity_platform.config.settings import Settings

    user = await _make_user(repos, db_session, "session-limit-strict@example.com")
    settings = Settings(secret_key="x" * 32, max_concurrent_sessions_per_user=1)
    service = SessionService(repos, settings=settings)

    await service.create_session(user.id)
    await db_session.commit()

    with pytest.raises(ConcurrentSessionLimitExceededError):
        await service.create_session(user.id, evict_oldest=False)
