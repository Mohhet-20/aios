"""Gateway security policy management: a generic policy row per
(tenant, name) spanning the six policy types the prompt specifies
(ip_filter, geo_restriction, rate_limit, request_signing,
bot_detection, threat_detection). `register_policy` is a get-or-create
by name, since re-registering the same named policy should update its
rules rather than create a duplicate row. Status is a simple
active/inactive field guarded directly in-service, the same
"simpler status fields" precedent used throughout this platform."""
from __future__ import annotations

from gateway_platform.core.exceptions import SecurityPolicyNotFoundError, ValidationError
from gateway_platform.domain.enums import SecurityPolicyType
from gateway_platform.models.security import GatewaySecurityPolicyModel
from gateway_platform.repositories.registry import RepositoryRegistry


class SecurityPolicyService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    def _assert_valid_type(self, policy_type: str) -> None:
        try:
            SecurityPolicyType(policy_type)
        except ValueError as exc:
            raise ValidationError(f"'{policy_type}' is not a supported security policy type") from exc

    async def register_policy(
        self, tenant_id: str, *, name: str, policy_type: str, rules: dict | None = None,
    ) -> GatewaySecurityPolicyModel:
        self._assert_valid_type(policy_type)
        for existing in await self.repos.security_policies.list_for_tenant(tenant_id, policy_type=policy_type):
            if existing.name == name:
                existing.rules = rules or existing.rules
                return await self.repos.security_policies.update(existing)
        policy = GatewaySecurityPolicyModel(
            tenant_id=tenant_id, name=name, policy_type=policy_type, status="active", rules=rules or {},
        )
        return await self.repos.security_policies.add(policy)

    async def activate_policy(self, tenant_id: str, policy_id: str) -> GatewaySecurityPolicyModel:
        policy = await self._get_or_404(tenant_id, policy_id)
        policy.status = "active"
        return await self.repos.security_policies.update(policy)

    async def deactivate_policy(self, tenant_id: str, policy_id: str) -> GatewaySecurityPolicyModel:
        policy = await self._get_or_404(tenant_id, policy_id)
        policy.status = "inactive"
        return await self.repos.security_policies.update(policy)

    async def list_for_tenant(self, tenant_id: str, *, policy_type: str | None = None) -> list[GatewaySecurityPolicyModel]:
        return await self.repos.security_policies.list_for_tenant(tenant_id, policy_type=policy_type)

    async def _get_or_404(self, tenant_id: str, policy_id: str) -> GatewaySecurityPolicyModel:
        policy = await self.repos.security_policies.get_or_404(policy_id)
        if policy.tenant_id != tenant_id:
            raise SecurityPolicyNotFoundError(f"security policy '{policy_id}' not found for tenant '{tenant_id}'")
        return policy
