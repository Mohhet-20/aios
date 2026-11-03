import pytest

from identity_platform.authentication.email_verification_service import EmailVerificationService
from identity_platform.authentication.login_service import LoginService
from identity_platform.authentication.magic_link_service import MagicLinkService
from identity_platform.authentication.password_service import PasswordService
from identity_platform.authentication.registration_service import RegistrationService
from identity_platform.core.exceptions import InvalidCredentialsError, PasswordPolicyError

pytestmark = pytest.mark.asyncio

STRONG_PASSWORD = "Str0ng!Passw0rd#1"
NEW_STRONG_PASSWORD = "An0ther!Str0ngPass#2"


async def _register_and_activate(repos, db_session, email: str):
    reg = RegistrationService(repos)
    result = await reg.register(email=email, raw_password=STRONG_PASSWORD)
    await db_session.commit()
    verifier = EmailVerificationService(repos)
    user = await verifier.verify(result.raw_verification_token)
    await db_session.commit()
    return user


async def test_change_password_then_login_with_new_password(repos, db_session):
    await _register_and_activate(repos, db_session, "changepw@example.com")

    pw_service = PasswordService(repos)
    user = await repos.users.get_by_email("changepw@example.com")
    await pw_service.change_password(user.id, current_password=STRONG_PASSWORD, new_password=NEW_STRONG_PASSWORD)
    await db_session.commit()

    login = LoginService(repos)
    with pytest.raises(InvalidCredentialsError):
        await login.authenticate(email="changepw@example.com", raw_password=STRONG_PASSWORD)
    await db_session.commit()

    authed = await login.authenticate(email="changepw@example.com", raw_password=NEW_STRONG_PASSWORD)
    assert authed.email == "changepw@example.com"


async def test_change_password_rejects_reused_password(repos, db_session):
    await _register_and_activate(repos, db_session, "reusepw@example.com")
    user = await repos.users.get_by_email("reusepw@example.com")

    pw_service = PasswordService(repos)
    with pytest.raises(PasswordPolicyError):
        await pw_service.change_password(user.id, current_password=STRONG_PASSWORD, new_password=STRONG_PASSWORD)


async def test_password_reset_flow(repos, db_session):
    await _register_and_activate(repos, db_session, "forgot@example.com")

    pw_service = PasswordService(repos)
    raw_token = await pw_service.request_reset("forgot@example.com")
    await db_session.commit()
    assert raw_token is not None

    await pw_service.reset_with_token(raw_token, NEW_STRONG_PASSWORD)
    await db_session.commit()

    login = LoginService(repos)
    authed = await login.authenticate(email="forgot@example.com", raw_password=NEW_STRONG_PASSWORD)
    assert authed.email == "forgot@example.com"


async def test_password_reset_for_unknown_email_returns_none(repos, db_session):
    pw_service = PasswordService(repos)
    result = await pw_service.request_reset("nobody@example.com")
    assert result is None


async def test_magic_link_login_flow(repos, db_session):
    await _register_and_activate(repos, db_session, "magic@example.com")

    magic = MagicLinkService(repos)
    raw_token = await magic.request_link("magic@example.com")
    await db_session.commit()
    assert raw_token is not None

    user = await magic.redeem(raw_token)
    await db_session.commit()
    assert user.email == "magic@example.com"
    assert user.last_login_at is not None
