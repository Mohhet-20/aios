import pytest

from identity_platform.domain.enums import SecurityEventSeverity, SecurityEventType, SecurityPolicyType
from identity_platform.security_platform.policy_service import SecurityPolicyService
from identity_platform.security_platform.security_event_service import SecurityEventService

pytestmark = pytest.mark.asyncio


async def test_set_and_get_effective_policy_org_specific(repos, db_session):
    service = SecurityPolicyService(repos)
    await service.set_policy(
        "org-1", SecurityPolicyType.IP_RESTRICTION, config={"mode": "allow", "values": ["10.0.0.0/8"]},
    )
    await db_session.commit()

    config = await service.get_effective_config("org-1", SecurityPolicyType.IP_RESTRICTION)
    assert config == {"mode": "allow", "values": ["10.0.0.0/8"]}


async def test_falls_back_to_platform_default_when_no_org_policy(repos, db_session):
    service = SecurityPolicyService(repos)
    await service.set_policy(None, SecurityPolicyType.GEO_RESTRICTION, config={"mode": "deny", "values": ["KP"]})
    await db_session.commit()

    config = await service.get_effective_config("some-org-with-no-policy", SecurityPolicyType.GEO_RESTRICTION)
    assert config == {"mode": "deny", "values": ["KP"]}


async def test_set_policy_updates_existing_row_for_same_org_and_type(repos, db_session):
    service = SecurityPolicyService(repos)
    await service.set_policy("org-2", SecurityPolicyType.SESSION, config={"max_sessions": 5})
    await db_session.commit()
    await service.set_policy("org-2", SecurityPolicyType.SESSION, config={"max_sessions": 10})
    await db_session.commit()

    policies = await service.list_for_organization("org-2")
    session_policies = [p for p in policies if p.policy_type == "session"]
    assert len(session_policies) == 1
    assert session_policies[0].config == {"max_sessions": 10}


async def test_deactivated_policy_is_not_effective(repos, db_session):
    service = SecurityPolicyService(repos)
    policy = await service.set_policy("org-3", SecurityPolicyType.MFA_REQUIREMENT, config={"required": True})
    await db_session.commit()

    await service.deactivate(policy.id)
    await db_session.commit()

    config = await service.get_effective_config("org-3", SecurityPolicyType.MFA_REQUIREMENT)
    assert config is None


async def test_record_and_resolve_security_event(repos, db_session):
    service = SecurityEventService(repos)
    event = await service.record_event(
        event_type=SecurityEventType.BRUTE_FORCE, severity=SecurityEventSeverity.WARNING,
        organization_id="org-4", user_id="user-1", details={"attempts": 6},
    )
    await db_session.commit()
    assert event.resolved is False

    unresolved = await service.list_unresolved("org-4")
    assert any(e.id == event.id for e in unresolved)

    await service.resolve_event(event.id)
    await db_session.commit()

    unresolved_after = await service.list_unresolved("org-4")
    assert all(e.id != event.id for e in unresolved_after)
