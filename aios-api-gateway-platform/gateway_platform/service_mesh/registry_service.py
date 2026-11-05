"""Service Discovery & Registry: services register themselves once
(get-or-create by name, so a redeploying service re-announcing itself
doesn't create a duplicate registration) and then register one
instance row per routable endpoint. Status on both is a simple field
guarded directly here rather than through a dedicated domain entity —
the same "simpler status fields guarded in-service" precedent used for
node pools and other lightly-stated resources in the Infrastructure
Platform."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from gateway_platform.core.exceptions import (
    InvalidTransitionError,
    ServiceInstanceNotFoundError,
    ServiceNotFoundError,
)
from gateway_platform.domain.enums import InstanceStatus, ServiceStatus
from gateway_platform.models.mesh import ServiceInstanceModel, ServiceRegistrationModel
from gateway_platform.repositories.registry import RepositoryRegistry

_SERVICE_TRANSITIONS: dict[ServiceStatus, set[ServiceStatus]] = {
    ServiceStatus.REGISTERED: {ServiceStatus.HEALTHY, ServiceStatus.UNHEALTHY},
    ServiceStatus.HEALTHY: {ServiceStatus.UNHEALTHY, ServiceStatus.DEREGISTERED},
    ServiceStatus.UNHEALTHY: {ServiceStatus.HEALTHY, ServiceStatus.DEREGISTERED},
    ServiceStatus.DEREGISTERED: set(),
}

_INSTANCE_TRANSITIONS: dict[InstanceStatus, set[InstanceStatus]] = {
    InstanceStatus.ACTIVE: {InstanceStatus.DRAINING, InstanceStatus.UNHEALTHY, InstanceStatus.REMOVED},
    InstanceStatus.DRAINING: {InstanceStatus.REMOVED},
    InstanceStatus.UNHEALTHY: {InstanceStatus.ACTIVE, InstanceStatus.REMOVED},
    InstanceStatus.REMOVED: set(),
}


class ServiceRegistryService:
    """`register_service` is a get-or-create keyed on `(tenant_id,
    name)` — guarded with an in-process `asyncio.Lock` per key, the
    same commit-spanning-lock pattern used across every other AIOS
    services's own "upsert by identity" methods, since two concurrent
    callers registering the same service name for the first time
    (e.g. two instances of the same service redeploying and
    re-announcing simultaneously) would otherwise both observe no
    existing row and both insert, producing a duplicate registration."""

    _register_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def register_service(self, tenant_id: str, *, name: str, metadata: dict | None = None) -> ServiceRegistrationModel:
        lock_key = f"{tenant_id}:{name}"
        async with self._register_locks[lock_key]:
            existing = await self.repos.services.get_by_name(tenant_id, name)
            if existing is not None:
                return existing
            service = ServiceRegistrationModel(tenant_id=tenant_id, name=name, service_metadata=metadata or {})
            service = await self.repos.services.add(service)
            # Commit while still holding the lock — see ConnectorService's
            # identical note on why this must happen before release.
            await self.repos.session.commit()
            return service

    async def mark_healthy(self, tenant_id: str, service_id: str) -> ServiceRegistrationModel:
        return await self._transition_service(tenant_id, service_id, ServiceStatus.HEALTHY)

    async def mark_unhealthy(self, tenant_id: str, service_id: str) -> ServiceRegistrationModel:
        return await self._transition_service(tenant_id, service_id, ServiceStatus.UNHEALTHY)

    async def deregister_service(self, tenant_id: str, service_id: str) -> ServiceRegistrationModel:
        return await self._transition_service(tenant_id, service_id, ServiceStatus.DEREGISTERED)

    async def register_instance(
        self, tenant_id: str, service_id: str, *, host: str, port: int = 80, weight: int = 1,
    ) -> ServiceInstanceModel:
        instance = ServiceInstanceModel(
            tenant_id=tenant_id, service_id=service_id, host=host, port=port, weight=weight,
            status=InstanceStatus.ACTIVE.value,
        )
        return await self.repos.service_instances.add(instance)

    async def transition_instance(self, tenant_id: str, instance_id: str, target: InstanceStatus) -> ServiceInstanceModel:
        instance = await self._get_instance_or_404(tenant_id, instance_id)
        current = InstanceStatus(instance.status)
        if target not in _INSTANCE_TRANSITIONS.get(current, set()):
            raise InvalidTransitionError(f"ServiceInstance '{instance_id}' cannot move from {current.value} to {target.value}")
        instance.status = target.value
        return await self.repos.service_instances.update(instance)

    async def list_instances(self, tenant_id: str, service_id: str, *, status: str | None = None) -> list[ServiceInstanceModel]:
        return await self.repos.service_instances.list_for_service(tenant_id, service_id, status=status)

    async def list_services(self, tenant_id: str) -> list[ServiceRegistrationModel]:
        return await self.repos.services.list_for_tenant(tenant_id)

    async def _transition_service(self, tenant_id: str, service_id: str, target: ServiceStatus) -> ServiceRegistrationModel:
        service = await self._get_service_or_404(tenant_id, service_id)
        current = ServiceStatus(service.status)
        if target not in _SERVICE_TRANSITIONS.get(current, set()):
            raise InvalidTransitionError(f"Service '{service_id}' cannot move from {current.value} to {target.value}")
        service.status = target.value
        return await self.repos.services.update(service)

    async def _get_service_or_404(self, tenant_id: str, service_id: str) -> ServiceRegistrationModel:
        service = await self.repos.services.get_or_404(service_id)
        if service.tenant_id != tenant_id:
            raise ServiceNotFoundError(f"service '{service_id}' not found for tenant '{tenant_id}'")
        return service

    async def _get_instance_or_404(self, tenant_id: str, instance_id: str) -> ServiceInstanceModel:
        instance = await self.repos.service_instances.get_or_404(instance_id)
        if instance.tenant_id != tenant_id:
            raise ServiceInstanceNotFoundError(f"service instance '{instance_id}' not found for tenant '{tenant_id}'")
        return instance
