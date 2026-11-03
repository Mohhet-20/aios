"""IP filtering: real CIDR-range matching via the stdlib `ipaddress`
module (not a substring/prefix hack). Rules are evaluated in
insertion order, first match wins; if nothing matches, the tenant's
`security_ip_filter_default_mode` setting decides ("allow_all" or
"deny_all")."""
from __future__ import annotations

import ipaddress

from gateway_platform.config.settings import Settings, get_settings
from gateway_platform.core.exceptions import IpBlockedError
from gateway_platform.models.security import IpRuleModel
from gateway_platform.repositories.registry import RepositoryRegistry


class IpFilterService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def add_rule(self, tenant_id: str, policy_id: str, *, cidr: str, action: str = "deny") -> IpRuleModel:
        ipaddress.ip_network(cidr, strict=False)  # raises ValueError if malformed
        rule = IpRuleModel(tenant_id=tenant_id, policy_id=policy_id, cidr=cidr, action=action)
        return await self.repos.ip_rules.add(rule)

    async def list_rules(self, tenant_id: str, policy_id: str) -> list[IpRuleModel]:
        return await self.repos.ip_rules.list_for_policy(tenant_id, policy_id)

    async def evaluate(self, tenant_id: str, policy_id: str, ip_address: str) -> bool:
        """Returns True if the address is allowed; raises `IpBlockedError`
        if a matching rule (or the default mode) denies it."""
        candidate = ipaddress.ip_address(ip_address)
        for rule in await self.list_rules(tenant_id, policy_id):
            network = ipaddress.ip_network(rule.cidr, strict=False)
            if candidate in network:
                if rule.action == "deny":
                    raise IpBlockedError(f"IP '{ip_address}' is blocked by rule matching '{rule.cidr}'")
                return True

        if self.settings.security_ip_filter_default_mode == "deny_all":
            raise IpBlockedError(f"IP '{ip_address}' denied by default-deny policy '{policy_id}'")
        return True
