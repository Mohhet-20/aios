"""Ordered developer RBAC: viewer < operator < admin, with optional
per-scope bindings (e.g. scope="plugin:my-plugin" grants a role only
over that resource) falling back to a tenant-wide binding
(scope=None) when no scope-specific binding exists — the same
ordered-role-with-scope-fallback pattern used by every sibling AIOS
platform's own lightweight RBAC."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from developer_platform.core.exceptions import PermissionDeniedError
from developer_platform.domain.enums import DeveloperRole
from developer_platform.models.security import DeveloperRoleBindingModel
from developer_platform.repositories.registry import RepositoryRegistry


class DeveloperRbacService:
    """`grant_role` is an upsert keyed on `(tenant_id, principal_id,
    scope)` — guarded with an in-process `asyncio.Lock` per key, the
    same commit-spanning-lock pattern used across every other AIOS
    services's own upsert-by-identity methods, so two concurrent
    grants for the same principal/scope can never both observe no
    existing binding and both insert a duplicate row."""

    _grant_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def grant_role(
        self, tenant_id: str, *, principal_id: str, role: str, scope: str | None = None,
    ) -> DeveloperRoleBindingModel:
        lock_key = f"{tenant_id}:{principal_id}:{scope}"
        async with self._grant_locks[lock_key]:
            existing = await self.repos.developer_role_bindings.get_for_principal(tenant_id, principal_id, scope)
            if existing is not None:
                existing.role = role
                binding = await self.repos.developer_role_bindings.update(existing)
            else:
                binding = DeveloperRoleBindingModel(tenant_id=tenant_id, principal_id=principal_id, role=role, scope=scope)
                binding = await self.repos.developer_role_bindings.add(binding)
            # Commit while still holding the lock — see
            # `PluginLifecycleService.register_plugin` for why.
            await self.repos.session.commit()
            return binding

    async def get_effective_role(self, tenant_id: str, principal_id: str, *, scope: str | None = None) -> DeveloperRole | None:
        if scope is not None:
            scoped = await self.repos.developer_role_bindings.get_for_principal(tenant_id, principal_id, scope)
            if scoped is not None:
                return DeveloperRole(scoped.role)
        global_binding = await self.repos.developer_role_bindings.get_for_principal(tenant_id, principal_id, None)
        return DeveloperRole(global_binding.role) if global_binding is not None else None

    async def require_role(
        self, tenant_id: str, principal_id: str, *, minimum_role: str, scope: str | None = None,
    ) -> DeveloperRole:
        effective = await self.get_effective_role(tenant_id, principal_id, scope=scope)
        minimum = DeveloperRole(minimum_role)
        if effective is None or effective.rank < minimum.rank:
            raise PermissionDeniedError(
                f"principal '{principal_id}' requires at least '{minimum.value}' "
                f"(has '{effective.value if effective else 'none'}')"
            )
        return effective

    async def list_for_principal(self, tenant_id: str, principal_id: str) -> list[DeveloperRoleBindingModel]:
        return await self.repos.developer_role_bindings.list_for_principal(tenant_id, principal_id)
