from datetime import timedelta

import pytest

from identity_platform.api_keys.api_key_service import ApiKeyService
from identity_platform.authorization.bootstrap import seed_builtin_roles
from identity_platform.authentication.login_service import LoginService
from identity_platform.authentication.email_verification_service import EmailVerificationService
from identity_platform.authentication.registration_service import RegistrationService
from identity_platform.database.base import utcnow
from identity_platform.domain.enums import SecurityEventSeverity, SecurityEventType, UserStatus
from identity_platform.models.user import UserModel
from identity_platform.observability.metrics_service import ObservabilityMetricsService
from identity_platform.organizations.organization_service import OrganizationService
from identity_platform.organizations.workspace_service import WorkspaceService
from identity_platform.security_platform.security_event_service import SecurityEventService
from identity_platform.sessions.session_service import SessionService

pytestmark = pytest.mark.asyncio

STRONG_PASSWORD = "Str0ng!Passw0rd#1"


async def _make_org(repos, db_session, name: str, email: str):
    owner = UserModel(email=email, status=UserStatus.ACTIVE.value)
    await repos.users.add(owner)
    await db_session.commit()
    org = await OrganizationService(repos).create_organization(name=name, owner_user_id=owner.id)
    await db_session.commit()
    return org, owner


async def test_auth_metrics_reflects_success_and_failure(repos, db_session):
    reg = RegistrationService(repos)
    result = await reg.register(email="metrics-auth@example.com", raw_password=STRONG_PASSWORD)
    await db_session.commit()
    await EmailVerificationService(repos).verify(result.raw_verification_token)
    await db_session.commit()

    login = LoginService(repos)
    await login.authenticate(email="metrics-auth@example.com", raw_password=STRONG_PASSWORD)
    await db_session.commit()
    with pytest.raises(Exception):
        await login.authenticate(email="metrics-auth@example.com", raw_password="wrong-password")
    await db_session.commit()

    metrics_service = ObservabilityMetricsService(repos)
    metrics = await metrics_service.auth_metrics()
    assert metrics["total_attempts"] >= 2
    assert metrics["successes"] >= 1
    assert metrics["failures"] >= 1
    assert 0 <= metrics["success_rate"] <= 1


async def test_session_metrics_counts_active_sessions(repos, db_session):
    org, owner = await _make_org(repos, db_session, "Metrics Session Co", "metrics-session-owner@example.com")
    session_service = SessionService(repos)
    await session_service.create_session(owner.id)
    await db_session.commit()

    metrics_service = ObservabilityMetricsService(repos)
    metrics = await metrics_service.session_metrics()
    assert metrics["active_sessions"] >= 1


async def test_api_key_usage_metrics(repos, db_session):
    org, owner = await _make_org(repos, db_session, "Metrics ApiKey Co", "metrics-apikey-owner@example.com")
    api_key_service = ApiKeyService(repos)
    await api_key_service.issue_key(org.id, owner_type="user", owner_id=owner.id, name="Key", created_by=owner.id)
    await db_session.commit()

    metrics_service = ObservabilityMetricsService(repos)
    usage = await metrics_service.api_key_usage(org.id)
    assert usage["total_keys"] == 1
    assert usage["active_keys"] == 1


async def test_organization_growth(repos, db_session):
    since = utcnow() - timedelta(days=1)
    await _make_org(repos, db_session, "Growth Co", "growth-owner@example.com")

    metrics_service = ObservabilityMetricsService(repos)
    growth = await metrics_service.organization_growth(since=since)
    assert growth["new_organizations"] >= 1
    assert growth["total_organizations"] >= growth["new_organizations"]


async def test_workspace_activity(repos, db_session):
    org, owner = await _make_org(repos, db_session, "Metrics WS Co", "metrics-ws-owner@example.com")
    ws_service = WorkspaceService(repos)
    workspace = await ws_service.create_workspace(org.id, name="WS")
    await db_session.commit()
    await ws_service.archive(workspace.id)
    await db_session.commit()

    metrics_service = ObservabilityMetricsService(repos)
    activity = await metrics_service.workspace_activity(org.id)
    assert activity["archived_workspaces"] == 1
    assert activity["active_workspaces"] == 0


async def test_permission_usage_metrics(repos, db_session):
    await seed_builtin_roles(repos)
    await db_session.commit()
    org, owner = await _make_org(repos, db_session, "Metrics Perm Co", "metrics-perm-owner@example.com")

    metrics_service = ObservabilityMetricsService(repos)
    usage = await metrics_service.permission_usage(org.id)
    assert any(entry["role_slug"] == "org_owner" and entry["active_assignments"] == 1 for entry in usage)


async def test_security_overview(repos, db_session):
    org, owner = await _make_org(repos, db_session, "Metrics Security Co", "metrics-security-owner@example.com")
    event_service = SecurityEventService(repos)
    await event_service.record_event(
        event_type=SecurityEventType.SUSPICIOUS_LOGIN, severity=SecurityEventSeverity.WARNING,
        organization_id=org.id, user_id=owner.id,
    )
    await db_session.commit()

    metrics_service = ObservabilityMetricsService(repos)
    overview = await metrics_service.security_overview(org.id)
    assert overview["total_events"] == 1
    assert overview["unresolved_count"] == 1
    assert overview["events_by_severity"]["warning"] == 1
