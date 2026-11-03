"""Tests for Infra Security & Governance: network policy evaluation,
runtime policy evaluation, and ordered RBAC role bindings/permission
checks."""
from __future__ import annotations

import pytest

from infra_platform.core.exceptions import NetworkPolicyViolationError, NotFoundError, PermissionDeniedError, RuntimePolicyViolationError
from infra_platform.infra_security.security_service import InfraRoleBindingService, NetworkPolicyService, RuntimePolicyService

TENANT = "tenant-infra-security"


@pytest.mark.asyncio
async def test_network_policy_denies_configured_destination(repos):
    service = NetworkPolicyService(repos)
    await service.create_policy(TENANT, name="deny-external", rules={"deny_destinations": ["10.0.0.1", "evil.example.com"]})

    with pytest.raises(NetworkPolicyViolationError):
        await service.evaluate_connection(TENANT, destination="evil.example.com")

    assert await service.evaluate_connection(TENANT, destination="internal.svc.cluster.local") is True


@pytest.mark.asyncio
async def test_disabled_network_policy_not_enforced(repos):
    service = NetworkPolicyService(repos)
    policy = await service.create_policy(TENANT, name="temp-deny", rules={"deny_destinations": ["10.0.0.2"]})
    await service.disable(TENANT, policy.id)

    assert await service.evaluate_connection(TENANT, destination="10.0.0.2") is True

    await service.enable(TENANT, policy.id)
    with pytest.raises(NetworkPolicyViolationError):
        await service.evaluate_connection(TENANT, destination="10.0.0.2")


@pytest.mark.asyncio
async def test_runtime_policy_cpu_and_privileged_violations(repos):
    service = RuntimePolicyService(repos)
    await service.create_policy(TENANT, name="cpu-cap", policy_type="resource_limit", rules={"max_cpu": 4})
    await service.create_policy(TENANT, name="no-privileged", policy_type="seccomp", rules={"allow_privileged": False})

    with pytest.raises(RuntimePolicyViolationError):
        await service.evaluate(TENANT, context={"cpu_requested": 8})

    with pytest.raises(RuntimePolicyViolationError):
        await service.evaluate(TENANT, context={"cpu_requested": 1, "privileged": True})

    assert await service.evaluate(TENANT, context={"cpu_requested": 2, "privileged": False}) is True


@pytest.mark.asyncio
async def test_role_binding_grant_upsert_and_permission_check(repos):
    service = InfraRoleBindingService(repos)
    await service.grant_role(TENANT, principal_id="user-1", role="viewer", scope="cluster-a")

    with pytest.raises(PermissionDeniedError):
        await service.check_permission(TENANT, principal_id="user-1", required_role="operator", scope="cluster-a")

    await service.grant_role(TENANT, principal_id="user-1", role="admin", scope="cluster-a")
    binding = await service.check_permission(TENANT, principal_id="user-1", required_role="operator", scope="cluster-a")
    assert binding.role == "admin"

    bindings = await service.list_for_principal(TENANT, "user-1")
    assert len(bindings) == 1  # upsert, not duplicate


@pytest.mark.asyncio
async def test_permission_denied_without_binding(repos):
    service = InfraRoleBindingService(repos)
    with pytest.raises(PermissionDeniedError):
        await service.check_permission(TENANT, principal_id="ghost-user", required_role="viewer", scope=None)


@pytest.mark.asyncio
async def test_revoke_role(repos):
    service = InfraRoleBindingService(repos)
    await service.grant_role(TENANT, principal_id="user-2", role="operator", scope=None)
    await service.revoke_role(TENANT, principal_id="user-2", scope=None)

    with pytest.raises(NotFoundError):
        await service.revoke_role(TENANT, principal_id="user-2", scope=None)


@pytest.mark.asyncio
async def test_grant_role_unknown_role_raises(repos):
    service = InfraRoleBindingService(repos)
    with pytest.raises(NotFoundError):
        await service.grant_role(TENANT, principal_id="user-3", role="superadmin")
