"""Infra Security & Governance: network policies (namespace/cluster-
scoped ingress/egress rules), runtime policies (seccomp/apparmor/
resource-limit style constraints), and ordered infra RBAC (viewer <
operator < admin). Evaluation is deliberately simple rule matching —
"deny_destinations" for network policies, "max_cpu"/"allow_privileged"
for runtime policies — the same heuristic-not-ML-classifier posture
the Security Platform's guardrails disclosed; a real deployment would
back this with an actual CNI/admission-controller integration."""
from __future__ import annotations

from infra_platform.core.exceptions import (
    NetworkPolicyViolationError,
    NotFoundError,
    PermissionDeniedError,
    RuntimePolicyViolationError,
)
from infra_platform.domain.enums import InfraRole
from infra_platform.models.security import InfraRoleBindingModel, NetworkPolicyModel, RuntimePolicyModel
from infra_platform.repositories.registry import RepositoryRegistry

_VALID_ROLES = {r.value for r in InfraRole}


class NetworkPolicyService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_policy(
        self, tenant_id: str, *, name: str, cluster_id: str | None = None, namespace: str | None = None, rules: dict | None = None
    ) -> NetworkPolicyModel:
        policy = NetworkPolicyModel(
            tenant_id=tenant_id, cluster_id=cluster_id, namespace=namespace, name=name, rules=rules or {}, is_enabled=True
        )
        return await self.repos.network_policies.add(policy)

    async def _get(self, tenant_id: str, policy_id: str) -> NetworkPolicyModel:
        policy = await self.repos.network_policies.get(policy_id)
        if policy is None or policy.tenant_id != tenant_id:
            raise NotFoundError(f"NetworkPolicy '{policy_id}' not found")
        return policy

    async def disable(self, tenant_id: str, policy_id: str) -> NetworkPolicyModel:
        policy = await self._get(tenant_id, policy_id)
        policy.is_enabled = False
        return await self.repos.network_policies.update(policy)

    async def enable(self, tenant_id: str, policy_id: str) -> NetworkPolicyModel:
        policy = await self._get(tenant_id, policy_id)
        policy.is_enabled = True
        return await self.repos.network_policies.update(policy)

    async def list_enabled(self, tenant_id: str) -> list[NetworkPolicyModel]:
        return await self.repos.network_policies.list_enabled(tenant_id)

    async def evaluate_connection(self, tenant_id: str, *, destination: str) -> bool:
        """Raises `NetworkPolicyViolationError` if any enabled policy
        denies `destination`; otherwise returns True."""
        policies = await self.repos.network_policies.list_enabled(tenant_id)
        for policy in policies:
            denied = policy.rules.get("deny_destinations", [])
            if destination in denied:
                raise NetworkPolicyViolationError(f"Connection to '{destination}' denied by network policy '{policy.name}'")
        return True


class RuntimePolicyService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_policy(
        self, tenant_id: str, *, name: str, policy_type: str, rules: dict | None = None
    ) -> RuntimePolicyModel:
        policy = RuntimePolicyModel(tenant_id=tenant_id, name=name, policy_type=policy_type, rules=rules or {}, is_enabled=True)
        return await self.repos.runtime_policies.add(policy)

    async def _get(self, tenant_id: str, policy_id: str) -> RuntimePolicyModel:
        policy = await self.repos.runtime_policies.get(policy_id)
        if policy is None or policy.tenant_id != tenant_id:
            raise NotFoundError(f"RuntimePolicy '{policy_id}' not found")
        return policy

    async def disable(self, tenant_id: str, policy_id: str) -> RuntimePolicyModel:
        policy = await self._get(tenant_id, policy_id)
        policy.is_enabled = False
        return await self.repos.runtime_policies.update(policy)

    async def enable(self, tenant_id: str, policy_id: str) -> RuntimePolicyModel:
        policy = await self._get(tenant_id, policy_id)
        policy.is_enabled = True
        return await self.repos.runtime_policies.update(policy)

    async def list_enabled(self, tenant_id: str) -> list[RuntimePolicyModel]:
        return await self.repos.runtime_policies.list_enabled(tenant_id)

    async def evaluate(self, tenant_id: str, *, context: dict) -> bool:
        """Raises `RuntimePolicyViolationError` on the first enabled
        policy whose rules `context` violates; otherwise returns True."""
        policies = await self.repos.runtime_policies.list_enabled(tenant_id)
        for policy in policies:
            max_cpu = policy.rules.get("max_cpu")
            if max_cpu is not None and context.get("cpu_requested", 0) > max_cpu:
                raise RuntimePolicyViolationError(
                    f"Runtime policy '{policy.name}' violated: cpu_requested {context.get('cpu_requested')} exceeds max_cpu {max_cpu}"
                )
            if policy.rules.get("allow_privileged") is False and context.get("privileged"):
                raise RuntimePolicyViolationError(f"Runtime policy '{policy.name}' violated: privileged containers not allowed")
        return True


class InfraRoleBindingService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def grant_role(
        self, tenant_id: str, *, principal_id: str, role: str, scope: str | None = None
    ) -> InfraRoleBindingModel:
        if role not in _VALID_ROLES:
            raise NotFoundError(f"Unknown infra role '{role}'")
        existing = await self.repos.infra_role_bindings.get_for_principal(tenant_id, principal_id, scope)
        if existing is not None:
            existing.role = role
            return await self.repos.infra_role_bindings.update(existing)
        binding = InfraRoleBindingModel(tenant_id=tenant_id, principal_id=principal_id, role=role, scope=scope)
        return await self.repos.infra_role_bindings.add(binding)

    async def revoke_role(self, tenant_id: str, *, principal_id: str, scope: str | None = None) -> None:
        existing = await self.repos.infra_role_bindings.get_for_principal(tenant_id, principal_id, scope)
        if existing is None:
            raise NotFoundError(f"No role binding for principal '{principal_id}' in scope '{scope}'")
        await self.repos.infra_role_bindings.delete(existing, hard=True)

    async def check_permission(
        self, tenant_id: str, *, principal_id: str, required_role: str, scope: str | None = None
    ) -> InfraRoleBindingModel:
        binding = await self.repos.infra_role_bindings.get_for_principal(tenant_id, principal_id, scope)
        if binding is None:
            raise PermissionDeniedError(f"Principal '{principal_id}' has no role binding in scope '{scope}'")
        if InfraRole(binding.role).rank < InfraRole(required_role).rank:
            raise PermissionDeniedError(
                f"Principal '{principal_id}' has role '{binding.role}', requires at least '{required_role}'"
            )
        return binding

    async def list_for_principal(self, tenant_id: str, principal_id: str) -> list[InfraRoleBindingModel]:
        return await self.repos.infra_role_bindings.list_for_principal(tenant_id, principal_id)
