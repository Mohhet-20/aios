from __future__ import annotations

import pytest

from gateway_platform.core.exceptions import InvalidTrafficWeightError, TrafficRuleNotFoundError, ValidationError
from gateway_platform.traffic.traffic_rule_service import TrafficRuleService

TENANT = "traffic-tenant"
ROUTE = "route-a"


@pytest.mark.asyncio
async def test_create_and_resolve_weighted_rule(repos):
    service = TrafficRuleService(repos, rand=lambda: 0.95)
    await service.create_rule(TENANT, ROUTE, rule_type="weighted", config={"weights": {"v1": 1, "v2": 9}})
    destination = await service.resolve_destination(TENANT, ROUTE)
    assert destination == "v2"


@pytest.mark.asyncio
async def test_invalid_rule_type_rejected(repos):
    service = TrafficRuleService(repos)
    with pytest.raises(ValidationError):
        await service.create_rule(TENANT, ROUTE, rule_type="teleport", config={})


@pytest.mark.asyncio
async def test_weighted_rule_requires_weights(repos):
    service = TrafficRuleService(repos)
    with pytest.raises(InvalidTrafficWeightError):
        await service.create_rule(TENANT, ROUTE, rule_type="weighted", config={})


@pytest.mark.asyncio
async def test_priority_ordering_across_multiple_rules(repos):
    service = TrafficRuleService(repos)
    await service.create_rule(TENANT, "route-b", rule_type="path", config={"prefix": "/beta", "destination": "beta-svc"}, priority=1)
    await service.create_rule(TENANT, "route-b", rule_type="region", config={"region_map": {}, "default": "region-svc"}, priority=0)

    beta_destination = await service.resolve_destination(TENANT, "route-b", context={"path": "/beta/x"})
    assert beta_destination == "beta-svc"

    fallback_destination = await service.resolve_destination(TENANT, "route-b", context={"path": "/stable/x"})
    assert fallback_destination == "region-svc"


@pytest.mark.asyncio
async def test_deactivated_rule_is_skipped(repos):
    service = TrafficRuleService(repos)
    rule = await service.create_rule(TENANT, "route-c", rule_type="failover", config={"primary": "v1", "fallback": "v2"})
    await service.deactivate_rule(TENANT, rule.id)
    with pytest.raises(TrafficRuleNotFoundError):
        await service.resolve_destination(TENANT, "route-c")

    await service.activate_rule(TENANT, rule.id)
    destination = await service.resolve_destination(TENANT, "route-c")
    assert destination == "v1"


@pytest.mark.asyncio
async def test_resolve_falls_back_to_default_when_no_rules(repos):
    service = TrafficRuleService(repos)
    destination = await service.resolve_destination(TENANT, "route-d", default="default-svc")
    assert destination == "default-svc"


@pytest.mark.asyncio
async def test_resolve_mirror_target(repos):
    service = TrafficRuleService(repos, rand=lambda: 0.1)
    await service.create_rule(
        TENANT, "route-e", rule_type="mirror", config={"primary": "v1", "mirror_to": "shadow", "sample_rate": 1.0},
    )
    mirror_target = await service.resolve_mirror_target(TENANT, "route-e")
    assert mirror_target == "shadow"


@pytest.mark.asyncio
async def test_list_for_route(repos):
    service = TrafficRuleService(repos)
    await service.create_rule(TENANT, "route-f", rule_type="blue_green", config={"active": "blue", "candidate": "green"})
    rules = await service.list_for_route(TENANT, "route-f")
    assert len(rules) == 1
