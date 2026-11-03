from __future__ import annotations

from datetime import timedelta

import pytest

from security_platform.core.exceptions import InvalidTransitionError, ValidationError
from security_platform.database.base import utcnow
from security_platform.policies.evaluation_service import PolicyEvaluationService
from security_platform.policies.exception_service import PolicyExceptionService
from security_platform.policies.policy_service import PolicyService


@pytest.mark.asyncio
async def test_create_policy_rejects_bad_scope_and_effect(repos):
    svc = PolicyService(repos)
    with pytest.raises(ValidationError):
        await svc.create_policy("t1", name="x", scope="not-a-scope")
    with pytest.raises(ValidationError):
        await svc.create_policy("t1", name="x", scope="organization", effect="not-an-effect")


@pytest.mark.asyncio
async def test_update_rules_creates_new_version(repos):
    svc = PolicyService(repos)
    policy = await svc.create_policy("t1", name="p1", scope="organization", rules={"a": 1})
    await svc.update_rules("t1", policy.id, rules={"a": 2})
    history = await svc.history("t1", policy.id)
    assert len(history) == 2
    assert history[0].version_number == 2  # newest first
    assert history[0].rules_snapshot == {"a": 2}


@pytest.mark.asyncio
async def test_policy_lifecycle_guarded(repos):
    svc = PolicyService(repos)
    policy = await svc.create_policy("t1", name="p1", scope="organization")
    await svc.activate("t1", policy.id)
    await svc.deprecate("t1", policy.id)
    await svc.archive("t1", policy.id)
    with pytest.raises(InvalidTransitionError):
        await svc.activate("t1", policy.id)


@pytest.mark.asyncio
async def test_exact_scope_policy_beats_broader_org_policy(repos):
    policy_svc = PolicyService(repos)
    org_policy = await policy_svc.create_policy("t1", name="org-deny-all-tools", scope="organization", effect="deny")
    await policy_svc.activate("t1", org_policy.id)

    tool_policy = await policy_svc.create_policy(
        "t1", name="allow-search-tool", scope="tool", scope_ref_id="tool-search", effect="allow"
    )
    await policy_svc.activate("t1", tool_policy.id)

    eval_svc = PolicyEvaluationService(repos)
    decision = await eval_svc.evaluate("t1", "tool", scope_ref_id="tool-search")
    assert decision.effect == "allow"
    assert decision.policy_id == tool_policy.id

    # A different tool with no specific policy falls back to the org-wide policy.
    decision2 = await eval_svc.evaluate("t1", "tool", scope_ref_id="tool-other")
    assert decision2.effect == "deny"
    assert decision2.policy_id == org_policy.id


@pytest.mark.asyncio
async def test_no_applicable_policy_defaults_to_allow(repos):
    eval_svc = PolicyEvaluationService(repos)
    decision = await eval_svc.evaluate("t1", "workflow", scope_ref_id="wf-1")
    assert decision.effect == "allow"
    assert decision.policy_id is None


@pytest.mark.asyncio
async def test_lower_priority_number_wins_among_ties(repos):
    policy_svc = PolicyService(repos)
    low_priority = await policy_svc.create_policy("t1", name="p-low", scope="agent", scope_ref_id="agent-1", effect="deny", priority=200)
    high_priority = await policy_svc.create_policy("t1", name="p-high", scope="agent", scope_ref_id="agent-1", effect="allow", priority=10)
    await policy_svc.activate("t1", low_priority.id)
    await policy_svc.activate("t1", high_priority.id)

    eval_svc = PolicyEvaluationService(repos)
    decision = await eval_svc.evaluate("t1", "agent", scope_ref_id="agent-1")
    assert decision.policy_id == high_priority.id
    assert decision.effect == "allow"


@pytest.mark.asyncio
async def test_active_exception_overrides_deny_policy(repos):
    policy_svc = PolicyService(repos)
    policy = await policy_svc.create_policy("t1", name="deny-agent", scope="agent", scope_ref_id="agent-2", effect="deny")
    await policy_svc.activate("t1", policy.id)

    exc_svc = PolicyExceptionService(repos)
    await exc_svc.grant_exception(
        "t1", policy.id, "agent-2", reason="temporary pilot", expires_at=utcnow() + timedelta(days=1)
    )

    eval_svc = PolicyEvaluationService(repos)
    decision = await eval_svc.evaluate("t1", "agent", scope_ref_id="agent-2")
    assert decision.effect == "allow"
    assert decision.exception_applied is True


@pytest.mark.asyncio
async def test_exception_expiry_cannot_exceed_max_days(repos):
    policy_svc = PolicyService(repos)
    policy = await policy_svc.create_policy("t1", name="deny-agent-2", scope="agent", scope_ref_id="agent-3", effect="deny")
    exc_svc = PolicyExceptionService(repos)
    with pytest.raises(ValidationError):
        await exc_svc.grant_exception(
            "t1", policy.id, "agent-3", reason="too long", expires_at=utcnow() + timedelta(days=9999)
        )


@pytest.mark.asyncio
async def test_expired_exception_does_not_apply(repos):
    policy_svc = PolicyService(repos)
    policy = await policy_svc.create_policy("t1", name="deny-agent-4", scope="agent", scope_ref_id="agent-4", effect="deny")
    await policy_svc.activate("t1", policy.id)

    from security_platform.models.policies import PolicyExceptionModel
    await repos.policy_exceptions.add(
        PolicyExceptionModel(
            tenant_id="t1", policy_id=policy.id, scope_ref_id="agent-4", reason="expired already",
            expires_at=utcnow() - timedelta(days=1),
        )
    )

    eval_svc = PolicyEvaluationService(repos)
    decision = await eval_svc.evaluate("t1", "agent", scope_ref_id="agent-4")
    assert decision.effect == "deny"
    assert decision.exception_applied is False
