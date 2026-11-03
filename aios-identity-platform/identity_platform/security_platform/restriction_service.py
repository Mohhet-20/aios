"""RestrictionService: evaluates IP-CIDR and country-code restrictions
against the org's `ip_restriction`/`geo_restriction` `SecurityPolicyModel`
config (or the platform default when the org hasn't set one). Config
shape: `{"mode": "allow"|"deny", "values": [...]}` — an "allow" list
permits only the listed values and denies everything else; a "deny"
list blocks only the listed values and permits everything else. No
policy configured (or an inactive one) means unrestricted."""
from __future__ import annotations

import ipaddress

from identity_platform.core.exceptions import GeoRestrictedError, IpRestrictedError
from identity_platform.domain.enums import SecurityPolicyType
from identity_platform.repositories.registry import RepositoryRegistry
from identity_platform.security_platform.policy_service import SecurityPolicyService


def _ip_matches_any_cidr(ip_address: str, cidrs: list[str]) -> bool:
    try:
        addr = ipaddress.ip_address(ip_address)
    except ValueError:
        return False
    for cidr in cidrs:
        try:
            if addr in ipaddress.ip_network(cidr, strict=False):
                return True
        except ValueError:
            continue
    return False


class RestrictionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.policy_service = SecurityPolicyService(repos)

    async def is_ip_allowed(self, organization_id: str | None, ip_address: str) -> bool:
        config = await self.policy_service.get_effective_config(organization_id, SecurityPolicyType.IP_RESTRICTION)
        if not config:
            return True
        values = config.get("values", [])
        matched = _ip_matches_any_cidr(ip_address, values)
        return matched if config.get("mode") == "allow" else not matched

    async def is_country_allowed(self, organization_id: str | None, country_code: str) -> bool:
        config = await self.policy_service.get_effective_config(organization_id, SecurityPolicyType.GEO_RESTRICTION)
        if not config:
            return True
        values = [v.upper() for v in config.get("values", [])]
        matched = country_code.upper() in values
        return matched if config.get("mode") == "allow" else not matched

    async def enforce_ip(self, organization_id: str | None, ip_address: str) -> None:
        if not await self.is_ip_allowed(organization_id, ip_address):
            raise IpRestrictedError(f"IP address '{ip_address}' is not permitted for this organization")

    async def enforce_country(self, organization_id: str | None, country_code: str) -> None:
        if not await self.is_country_allowed(organization_id, country_code):
            raise GeoRestrictedError(f"country '{country_code}' is not permitted for this organization")
