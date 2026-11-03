from __future__ import annotations

import pytest

from perf_platform.core.exceptions import NoEligibleModelTierError, UnsupportedTaskComplexityError
from perf_platform.routing.routing_service import ModelRoutingService, RoutingPolicyService

TENANT = "t-routing"


@pytest.mark.asyncio
async def test_route_persists_decision_with_cost_estimate(repos):
    svc = ModelRoutingService(repos)
    decision = await svc.route(TENANT, task_complexity="moderate", user_tier="pro")
    assert decision.chosen_tier == "medium"
    assert decision.estimated_cost_usd > 0
    recent = await svc.recent_decisions(TENANT)
    assert len(recent) == 1


@pytest.mark.asyncio
async def test_route_rejects_unsupported_complexity(repos):
    svc = ModelRoutingService(repos)
    with pytest.raises(UnsupportedTaskComplexityError):
        await svc.route(TENANT, task_complexity="impossible")


@pytest.mark.asyncio
async def test_route_uses_org_policy_when_present(repos):
    policy_svc = RoutingPolicyService(repos)
    await policy_svc.set_policy(TENANT, scope_type="organization", scope_id="org-9", allowed_tiers=["small"])

    routing_svc = ModelRoutingService(repos)
    decision = await routing_svc.route(
        TENANT, task_complexity="expert", user_tier="enterprise", policy_scope_type="organization", policy_scope_id="org-9",
    )
    assert decision.chosen_tier == "small"


@pytest.mark.asyncio
async def test_route_raises_when_policy_has_no_eligible_tier(repos):
    policy_svc = RoutingPolicyService(repos)
    await policy_svc.set_policy(TENANT, scope_type="workspace", scope_id="ws-impossible", allowed_tiers=["reasoning"])

    routing_svc = ModelRoutingService(repos)
    with pytest.raises(NoEligibleModelTierError):
        await routing_svc.route(
            TENANT, task_complexity="trivial", policy_scope_type="workspace", policy_scope_id="ws-impossible",
        )


@pytest.mark.asyncio
async def test_route_without_policy_scope_ignores_policy_lookup(repos):
    svc = ModelRoutingService(repos)
    decision = await svc.route(TENANT, task_complexity="simple")
    assert decision.chosen_tier == "small"
