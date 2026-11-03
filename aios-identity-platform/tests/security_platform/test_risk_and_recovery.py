import pytest

from identity_platform.config.settings import Settings
from identity_platform.domain.enums import UserStatus
from identity_platform.mfa.mfa_service import MfaService
from identity_platform.models.user import UserModel
from identity_platform.security.totp import generate_totp
from identity_platform.security_platform.account_recovery_service import AccountRecoveryService
from identity_platform.security_platform.risk_service import RiskScoringService, RiskSignals, compute_risk_score


def test_compute_risk_score_no_signals_is_zero():
    assert compute_risk_score(RiskSignals()) == 0.0


def test_compute_risk_score_new_device_and_country():
    score = compute_risk_score(RiskSignals(is_new_device=True, is_new_country=True))
    assert score == pytest.approx(0.6)


def test_compute_risk_score_caps_at_one():
    score = compute_risk_score(RiskSignals(
        is_new_device=True, is_new_country=True, impossible_travel=True, recent_failed_attempts=10,
    ))
    assert score == 1.0


@pytest.mark.asyncio
async def test_score_and_record_creates_event_above_threshold(repos, db_session):
    settings = Settings(secret_key="x" * 32, risk_score_high_threshold=0.5)
    service = RiskScoringService(repos, settings=settings)

    score = await service.score_and_record(
        user_id="user-risk-1", organization_id="org-risk", signals=RiskSignals(is_new_device=True, is_new_country=True),
    )
    await db_session.commit()
    assert score >= 0.5

    events = await service.security_event_service.list_for_user("user-risk-1")
    assert len(events) == 1
    assert events[0].event_type == "suspicious_login"


@pytest.mark.asyncio
async def test_score_and_record_no_event_below_threshold(repos, db_session):
    settings = Settings(secret_key="x" * 32, risk_score_high_threshold=0.99)
    service = RiskScoringService(repos, settings=settings)

    await service.score_and_record(user_id="user-risk-2", organization_id="org-risk", signals=RiskSignals(is_new_device=True))
    await db_session.commit()

    events = await service.security_event_service.list_for_user("user-risk-2")
    assert len(events) == 0


@pytest.mark.asyncio
async def test_admin_unlock_account(repos, db_session):
    from datetime import timedelta

    from identity_platform.database.base import utcnow

    user = UserModel(email="locked-user@example.com", status=UserStatus.LOCKED.value, locked_until=utcnow() + timedelta(minutes=30))
    await repos.users.add(user)
    await db_session.commit()

    recovery_service = AccountRecoveryService(repos)
    unlocked = await recovery_service.admin_unlock_account(user.id, performed_by="admin-1", organization_id="org-recovery")
    await db_session.commit()

    assert unlocked.status == "active"

    events = await recovery_service.security_event_service.list_for_user(user.id)
    assert any(e.details.get("action") == "admin_unlock" for e in events)


@pytest.mark.asyncio
async def test_admin_disable_mfa(repos, db_session):
    user = UserModel(email="mfa-recovery-user@example.com", status=UserStatus.ACTIVE.value)
    await repos.users.add(user)
    await db_session.commit()

    mfa_service = MfaService(repos)
    enrollment = await mfa_service.enroll_totp(user.id, account_email=user.email)
    await db_session.commit()
    await mfa_service.confirm_enrollment(enrollment.factor_id, generate_totp(enrollment.raw_secret))
    await db_session.commit()

    recovery_service = AccountRecoveryService(repos)
    disabled_count = await recovery_service.admin_disable_mfa(user.id, performed_by="admin-2")
    await db_session.commit()
    assert disabled_count == 1

    factor = await repos.mfa_factors.get(enrollment.factor_id)
    assert factor.status == "disabled"
