"""SecurityPolicyService: CRUD over the data-driven `SecurityPolicyModel`
rows (`policy_type` + `config` JSON) — one row per policy type per
organization, falling back to a platform-wide default
(`organization_id is None`) when an organization hasn't set its own.
The `config` shape is defined by convention per `policy_type` (e.g. an
`ip_restriction` policy's config is `{"mode": "allow"|"deny", "cidrs":
[...]}`); this service doesn't validate config shape beyond "it's a
dict," leaving that to the specific enforcement service that reads it
(`rate_limit_service.py`, `restriction_service.py`)."""
from __future__ import annotations

from identity_platform.domain.enums import SecurityPolicyType
from identity_platform.models.security import SecurityPolicyModel
from identity_platform.repositories.registry import RepositoryRegistry


class SecurityPolicyService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def set_policy(
        self, organization_id: str | None, policy_type: SecurityPolicyType, *, config: dict, is_active: bool = True,
    ) -> SecurityPolicyModel:
        existing = await self.repos.security_policies.get_effective(organization_id, policy_type.value)
        if existing is not None and existing.organization_id == organization_id:
            existing.config = config
            existing.is_active = is_active
            return await self.repos.security_policies.update(existing)

        return await self.repos.security_policies.add(SecurityPolicyModel(
            organization_id=organization_id, policy_type=policy_type.value, config=config, is_active=is_active,
        ))

    async def get_effective_config(self, organization_id: str | None, policy_type: SecurityPolicyType) -> dict | None:
        policy = await self.repos.security_policies.get_effective(organization_id, policy_type.value)
        if policy is None or not policy.is_active:
            return None
        return policy.config

    async def list_for_organization(self, organization_id: str | None) -> list[SecurityPolicyModel]:
        return await self.repos.security_policies.list_for_organization(organization_id)

    async def deactivate(self, policy_id: str) -> SecurityPolicyModel:
        policy = await self.repos.security_policies.get_or_404(policy_id)
        policy.is_active = False
        return await self.repos.security_policies.update(policy)
