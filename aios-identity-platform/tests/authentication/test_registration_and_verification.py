import pytest

from identity_platform.authentication.email_verification_service import EmailVerificationService
from identity_platform.authentication.registration_service import RegistrationService
from identity_platform.core.exceptions import ConflictError, PasswordPolicyError, TokenAlreadyUsedError

pytestmark = pytest.mark.asyncio

STRONG_PASSWORD = "Str0ng!Passw0rd#1"


async def test_register_creates_pending_user_with_verification_token(repos, db_session):
    service = RegistrationService(repos)
    result = await service.register(email="registrant@example.com", raw_password=STRONG_PASSWORD)
    await db_session.commit()

    assert result.user.email == "registrant@example.com"
    assert result.user.status == "pending_verification"
    assert result.raw_verification_token

    credential = await repos.password_credentials.get_for_user(result.user.id)
    assert credential is not None
    assert credential.password_hash != STRONG_PASSWORD


async def test_register_rejects_duplicate_email(repos, db_session):
    service = RegistrationService(repos)
    await service.register(email="dupe@example.com", raw_password=STRONG_PASSWORD)
    await db_session.commit()

    with pytest.raises(ConflictError):
        await service.register(email="DUPE@example.com", raw_password=STRONG_PASSWORD)


async def test_register_rejects_weak_password(repos, db_session):
    service = RegistrationService(repos)
    with pytest.raises(PasswordPolicyError):
        await service.register(email="weak@example.com", raw_password="short")


async def test_verify_email_transitions_user_to_active(repos, db_session):
    reg = RegistrationService(repos)
    result = await reg.register(email="verify@example.com", raw_password=STRONG_PASSWORD)
    await db_session.commit()

    verifier = EmailVerificationService(repos)
    user = await verifier.verify(result.raw_verification_token)
    await db_session.commit()

    assert user.status == "active"
    assert user.email_verified_at is not None


async def test_verify_email_rejects_reused_token(repos, db_session):
    reg = RegistrationService(repos)
    result = await reg.register(email="reuse@example.com", raw_password=STRONG_PASSWORD)
    await db_session.commit()

    verifier = EmailVerificationService(repos)
    await verifier.verify(result.raw_verification_token)
    await db_session.commit()

    with pytest.raises(TokenAlreadyUsedError):
        await verifier.verify(result.raw_verification_token)
