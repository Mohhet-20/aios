import pytest

from identity_platform.core.exceptions import ConflictError, InvalidMfaCodeError
from identity_platform.domain.enums import UserStatus
from identity_platform.mfa.device_trust_service import DeviceTrustService
from identity_platform.mfa.mfa_service import MfaService
from identity_platform.models.user import UserModel
from identity_platform.security.totp import generate_totp

pytestmark = pytest.mark.asyncio


async def _make_user(repos, db_session, email: str) -> UserModel:
    user = UserModel(email=email, status=UserStatus.ACTIVE.value)
    await repos.users.add(user)
    await db_session.commit()
    return user


async def test_enroll_and_confirm_totp_issues_recovery_codes(repos, db_session):
    user = await _make_user(repos, db_session, "mfa-enroll@example.com")
    service = MfaService(repos)

    enrollment = await service.enroll_totp(user.id, account_email=user.email)
    await db_session.commit()
    assert enrollment.provisioning_uri.startswith("otpauth://totp/")

    code = generate_totp(enrollment.raw_secret)
    recovery_codes = await service.confirm_enrollment(enrollment.factor_id, code)
    await db_session.commit()

    assert len(recovery_codes) == 10
    assert len(set(recovery_codes)) == 10

    factor = await repos.mfa_factors.get(enrollment.factor_id)
    assert factor.status == "active"


async def test_confirm_enrollment_rejects_wrong_code(repos, db_session):
    user = await _make_user(repos, db_session, "mfa-badcode@example.com")
    service = MfaService(repos)
    enrollment = await service.enroll_totp(user.id, account_email=user.email)
    await db_session.commit()

    with pytest.raises(InvalidMfaCodeError):
        await service.confirm_enrollment(enrollment.factor_id, "000000")


async def test_cannot_enroll_second_active_factor(repos, db_session):
    user = await _make_user(repos, db_session, "mfa-dupe@example.com")
    service = MfaService(repos)
    enrollment = await service.enroll_totp(user.id, account_email=user.email)
    await db_session.commit()
    code = generate_totp(enrollment.raw_secret)
    await service.confirm_enrollment(enrollment.factor_id, code)
    await db_session.commit()

    with pytest.raises(ConflictError):
        await service.enroll_totp(user.id, account_email=user.email)


async def test_verify_login_code_accepts_totp_and_recovery_code(repos, db_session):
    user = await _make_user(repos, db_session, "mfa-login@example.com")
    service = MfaService(repos)
    enrollment = await service.enroll_totp(user.id, account_email=user.email)
    await db_session.commit()
    recovery_codes = await service.confirm_enrollment(enrollment.factor_id, generate_totp(enrollment.raw_secret))
    await db_session.commit()

    fresh_code = generate_totp(enrollment.raw_secret)
    assert await service.verify_login_code(user.id, fresh_code) is True
    await db_session.commit()

    one_time = recovery_codes[0]
    assert await service.verify_login_code(user.id, one_time) is True
    await db_session.commit()

    # a used recovery code cannot be redeemed twice
    assert await service.redeem_recovery_code(user.id, one_time) is False

    remaining = await service.remaining_recovery_code_count(user.id)
    assert remaining == len(recovery_codes) - 1


async def test_disable_factor_transitions_to_disabled(repos, db_session):
    user = await _make_user(repos, db_session, "mfa-disable@example.com")
    service = MfaService(repos)
    enrollment = await service.enroll_totp(user.id, account_email=user.email)
    await db_session.commit()
    await service.confirm_enrollment(enrollment.factor_id, generate_totp(enrollment.raw_secret))
    await db_session.commit()

    disabled = await service.disable_factor(enrollment.factor_id)
    await db_session.commit()
    assert disabled.status == "disabled"


async def test_device_trust_roundtrip(repos, db_session):
    user = await _make_user(repos, db_session, "device-trust@example.com")
    service = DeviceTrustService(repos)

    raw_token = await service.trust_device(user.id, device_fingerprint="fp-123", device_name="Jane's MacBook")
    await db_session.commit()

    assert await service.is_trusted(user.id, raw_token) is True
    assert await service.is_trusted(user.id, "not-a-real-token") is False

    devices = await service.list_for_user(user.id)
    assert len(devices) == 1

    await service.revoke(devices[0].id)
    await db_session.commit()
    assert await service.is_trusted(user.id, raw_token) is False
