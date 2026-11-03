"""Traffic Management: one generic rule table covering all ten
routing strategies the prompt specifies, each carrying its own
free-form `config` shape (see `resolvers.py` for exactly what each
type expects). `resolve_destination` walks a route's active rules in
descending priority order and returns the first non-`None` resolution
— a rule that doesn't apply to this request (e.g. a header rule whose
header isn't present) is skipped rather than treated as a match, so
multiple rules can be stacked meaningfully (e.g. a region rule ahead
of a canary rule)."""
from __future__ import annotations

import random
from collections.abc import Callable

from gateway_platform.core.exceptions import InvalidTrafficWeightError, TrafficRuleNotFoundError, ValidationError
from gateway_platform.domain.enums import TrafficRuleType
from gateway_platform.models.traffic import TrafficRuleModel
from gateway_platform.repositories.registry import RepositoryRegistry
from gateway_platform.traffic.resolvers import RESOLVERS, should_mirror


def _assert_valid_config(rule_type: str, config: dict) -> None:
    if rule_type in ("weighted",) and not config.get("weights"):
        raise InvalidTrafficWeightError("weighted rule requires a non-empty 'weights' map")
    if rule_type == "split" and not config.get("splits"):
        raise InvalidTrafficWeightError("split rule requires a non-empty 'splits' map")
    if rule_type == "canary" and ("stable" not in config or "canary" not in config):
        raise ValidationError("canary rule requires 'stable' and 'canary' destinations")


class TrafficRuleService:
    def __init__(self, repos: RepositoryRegistry, *, rand: Callable[[], float] = random.random):
        self.repos = repos
        self._rand = rand

    def _assert_valid_type(self, rule_type: str) -> None:
        if rule_type not in {t.value for t in TrafficRuleType}:
            raise ValidationError(f"'{rule_type}' is not a recognized traffic rule type")

    async def create_rule(
        self, tenant_id: str, route_id: str, *, rule_type: str, config: dict, priority: int = 0,
    ) -> TrafficRuleModel:
        self._assert_valid_type(rule_type)
        _assert_valid_config(rule_type, config)
        rule = TrafficRuleModel(
            tenant_id=tenant_id, route_id=route_id, rule_type=rule_type, config=config, priority=priority,
            status="active",
        )
        return await self.repos.traffic_rules.add(rule)

    async def deactivate_rule(self, tenant_id: str, rule_id: str) -> TrafficRuleModel:
        rule = await self._get_or_404(tenant_id, rule_id)
        rule.status = "inactive"
        return await self.repos.traffic_rules.update(rule)

    async def activate_rule(self, tenant_id: str, rule_id: str) -> TrafficRuleModel:
        rule = await self._get_or_404(tenant_id, rule_id)
        rule.status = "active"
        return await self.repos.traffic_rules.update(rule)

    async def list_for_route(self, tenant_id: str, route_id: str) -> list[TrafficRuleModel]:
        return await self.repos.traffic_rules.list_for_route(tenant_id, route_id)

    async def resolve_destination(
        self, tenant_id: str, route_id: str, *, context: dict | None = None, default: str | None = None,
    ) -> str:
        context = context or {}
        rules = await self.repos.traffic_rules.list_for_route(tenant_id, route_id, status="active")
        for rule in rules:
            resolver = RESOLVERS.get(rule.rule_type)
            if resolver is None:
                continue
            destination = resolver(rule.config, context, self._rand)
            if destination is not None:
                return destination
        if default is not None:
            return default
        raise TrafficRuleNotFoundError(f"no traffic rule resolved a destination for route '{route_id}'")

    async def resolve_mirror_target(self, tenant_id: str, route_id: str) -> str | None:
        rules = await self.repos.traffic_rules.list_for_route(tenant_id, route_id, status="active")
        for rule in rules:
            if rule.rule_type == "mirror":
                return should_mirror(rule.config, self._rand)
        return None

    async def _get_or_404(self, tenant_id: str, rule_id: str) -> TrafficRuleModel:
        rule = await self.repos.traffic_rules.get_or_404(rule_id)
        if rule.tenant_id != tenant_id:
            raise TrafficRuleNotFoundError(f"traffic rule '{rule_id}' not found for tenant '{tenant_id}'")
        return rule
