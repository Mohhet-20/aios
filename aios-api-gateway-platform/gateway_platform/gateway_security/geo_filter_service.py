"""Geo restriction: rules keyed by ISO-3166-1 alpha-2 country code.
Same first-match-wins-with-default-mode-fallback shape as IP
filtering, but a plain equality check instead of CIDR containment
since country codes have no notion of "range"."""
from __future__ import annotations

from gateway_platform.config.settings import Settings, get_settings
from gateway_platform.core.exceptions import GeoBlockedError
from gateway_platform.models.security import GeoRuleModel
from gateway_platform.repositories.registry import RepositoryRegistry


class GeoFilterService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def add_rule(self, tenant_id: str, policy_id: str, *, country_code: str, action: str = "deny") -> GeoRuleModel:
        rule = GeoRuleModel(tenant_id=tenant_id, policy_id=policy_id, country_code=country_code.upper(), action=action)
        return await self.repos.geo_rules.add(rule)

    async def list_rules(self, tenant_id: str, policy_id: str) -> list[GeoRuleModel]:
        return await self.repos.geo_rules.list_for_policy(tenant_id, policy_id)

    async def evaluate(self, tenant_id: str, policy_id: str, country_code: str) -> bool:
        candidate = country_code.upper()
        for rule in await self.list_rules(tenant_id, policy_id):
            if rule.country_code == candidate:
                if rule.action == "deny":
                    raise GeoBlockedError(f"country '{candidate}' is blocked by policy '{policy_id}'")
                return True

        if self.settings.security_geo_restriction_default_mode == "deny_all":
            raise GeoBlockedError(f"country '{candidate}' denied by default-deny policy '{policy_id}'")
        return True
