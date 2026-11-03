import pytest

from identity_platform.authentication.email_verification_service import EmailVerificationService
from identity_platform.authentication.login_service import LoginService
from identity_platform.authentication.registration_service import RegistrationService
from identity_platform.config.settings import get_settings
from identity_platform.core.exceptions import AccountLockedError, AccountNotVerifiedError, InvalidCredentialsError

pytestmark = pytest.mark.asyncio

STRONG_PASSWORD = "Str0ng!Passw0rd#1"


async def _register_and_activate(repos, db_session, email: str):
    reg = RegistrationService(repos)
    result = await reg.register(email=email, raw_password=STRONG_PASSWORD)
    await db_session.commit()
    verifier = EmailVerificationService(repos)
    user = await verifier.verify(result.raw_verification_token)
    await db_session.commit()
    return user


async def test_login_succeeds_with_correct_credentials(repos, db_session):
    await _register_and_activate(repos, db_session, "login@example.com")

    login = LoginService(repos)
    user = await login.authenticate(email="login@example.com", raw_password=STRONG_PASSWORD)
    await db_session.commit()

    assert user.status == "active"
    assert user.last_login_at is not None
    assert user.failed_login_count == 0


async def test_login_fails_with_wrong_password(repos, db_session):
    await _register_and_activate(repos, db_session, "wrongpass@example.com")

    login = LoginService(repos)
    with pytest.raises(InvalidCredentialsError):
        await login.authenticate(email="wrongpass@example.com", raw_password="not-the-password")


async def test_login_fails_for_unknown_email(repos, db_session):
    login = LoginService(repos)
    with pytest.raises(InvalidCredentialsError):
        await login.authenticate(email="ghost@example.com", raw_password=STRONG_PASSWORD)


async def test_login_blocked_before_email_verification(repos, db_session):
    reg = RegistrationService(repos)
    await reg.register(email="unverified@example.com", raw_password=STRONG_PASSWORD)
    await db_session.commit()

    login = LoginService(repos)
    with pytest.raises(AccountNotVerifiedError):
        await login.authenticate(email="unverified@example.com", raw_password=STRONG_PASSWORD)


async def test_repeated_failures_lock_the_account(repos, db_session):
    await _register_and_activate(repos, db_session, "lockout@example.com")
    settings = get_settings()
    login = LoginService(repos)

    for _ in range(settings.account_lockout_threshold - 1):
        with pytest.raises(InvalidCredentialsError):
            await login.authenticate(email="lockout@example.com", raw_password="bad-password")
        await db_session.commit()

    with pytest.raises(AccountLockedError):
        await login.authenticate(email="lockout@example.com", raw_password="bad-password")
    await db_session.commit()

    # even the correct password is rejected while locked
    with pytest.raises(AccountLockedError):
        await login.authenticate(email="lockout@example.com", raw_password=STRONG_PASSWORD)
