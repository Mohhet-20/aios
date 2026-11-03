"""Inference Platform: real-time/batch/streaming/async inference
services on CPU or GPU compute, plus weighted routing rules across
service variants — the traffic-splitting primitive canary releases,
blue-green cutovers, and multi-model serving all build on.

`InferenceServiceModel.status` reuses the platform-wide `ServiceStatus`
lifecycle (provisioning -> running <-> degraded -> stopped ->
terminated) rather than a bespoke one, since an inference service is,
operationally, just another tracked runtime service."""
from __future__ import annotations

from infra_platform.core.exceptions import InferenceError, InferenceServiceUnavailableError, NotFoundError
from infra_platform.domain.enums import ServiceStatus
from infra_platform.models.inference import InferenceRouteModel, InferenceServiceModel
from infra_platform.repositories.registry import RepositoryRegistry

_SERVICE_TRANSITIONS: dict[str, set[str]] = {
    ServiceStatus.PROVISIONING.value: {ServiceStatus.RUNNING.value, ServiceStatus.STOPPED.value, ServiceStatus.TERMINATED.value},
    ServiceStatus.RUNNING.value: {ServiceStatus.DEGRADED.value, ServiceStatus.STOPPED.value, ServiceStatus.TERMINATED.value},
    ServiceStatus.DEGRADED.value: {ServiceStatus.RUNNING.value, ServiceStatus.STOPPED.value, ServiceStatus.TERMINATED.value},
    ServiceStatus.STOPPED.value: {ServiceStatus.RUNNING.value, ServiceStatus.TERMINATED.value},
    ServiceStatus.TERMINATED.value: set(),
}


class InferenceServiceService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def deploy_service(
        self, tenant_id: str, *, name: str, model_version_id: str | None = None, mode: str = "real_time",
        compute_type: str = "cpu", replicas: int = 1, endpoint_url: str | None = None,
    ) -> InferenceServiceModel:
        service = InferenceServiceModel(
            tenant_id=tenant_id, name=name, model_version_id=model_version_id, mode=mode, compute_type=compute_type,
            status=ServiceStatus.PROVISIONING.value, replicas=replicas, endpoint_url=endpoint_url,
        )
        return await self.repos.inference_services.add(service)

    async def _get(self, tenant_id: str, service_id: str) -> InferenceServiceModel:
        service = await self.repos.inference_services.get(service_id)
        if service is None or service.tenant_id != tenant_id:
            raise NotFoundError(f"InferenceService '{service_id}' not found")
        return service

    async def _transition(self, tenant_id: str, service_id: str, target: str) -> InferenceServiceModel:
        service = await self._get(tenant_id, service_id)
        allowed = _SERVICE_TRANSITIONS.get(service.status, set())
        if target not in allowed:
            raise InferenceError(f"InferenceService '{service_id}' cannot transition from {service.status} to {target}")
        service.status = target
        return await self.repos.inference_services.update(service)

    async def mark_running(self, tenant_id: str, service_id: str) -> InferenceServiceModel:
        return await self._transition(tenant_id, service_id, ServiceStatus.RUNNING.value)

    async def mark_degraded(self, tenant_id: str, service_id: str) -> InferenceServiceModel:
        return await self._transition(tenant_id, service_id, ServiceStatus.DEGRADED.value)

    async def stop(self, tenant_id: str, service_id: str) -> InferenceServiceModel:
        return await self._transition(tenant_id, service_id, ServiceStatus.STOPPED.value)

    async def terminate(self, tenant_id: str, service_id: str) -> InferenceServiceModel:
        return await self._transition(tenant_id, service_id, ServiceStatus.TERMINATED.value)

    async def ensure_available(self, tenant_id: str, service_id: str) -> InferenceServiceModel:
        service = await self._get(tenant_id, service_id)
        if service.status not in (ServiceStatus.RUNNING.value, ServiceStatus.DEGRADED.value):
            raise InferenceServiceUnavailableError(f"InferenceService '{service_id}' is {service.status}, not serving traffic")
        return service

    async def scale(self, tenant_id: str, service_id: str, *, replicas: int) -> InferenceServiceModel:
        if replicas < 0:
            raise InferenceError("replicas cannot be negative")
        service = await self.ensure_available(tenant_id, service_id)
        service.replicas = replicas
        return await self.repos.inference_services.update(service)

    async def list_for_tenant(self, tenant_id: str) -> list[InferenceServiceModel]:
        return await self.repos.inference_services.list_for_tenant(tenant_id)

    async def list_by_model_version(self, tenant_id: str, model_version_id: str) -> list[InferenceServiceModel]:
        return await self.repos.inference_services.list_by_model_version(tenant_id, model_version_id)


class InferenceRouteService:
    """Weighted traffic splitting across an inference service's
    variants. Active route weights must sum to 100 — the same
    invariant a canary step (5/25/50/100) or a blue-green cutover
    (0/100 -> 100/0) both reduce to."""

    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def add_route(
        self, tenant_id: str, inference_service_id: str, *, path: str, weight: int = 100, is_active: bool = True
    ) -> InferenceRouteModel:
        service = await self.repos.inference_services.get(inference_service_id)
        if service is None or service.tenant_id != tenant_id:
            raise NotFoundError(f"InferenceService '{inference_service_id}' not found")
        if not (0 <= weight <= 100):
            raise InferenceError("weight must be between 0 and 100")
        route = InferenceRouteModel(
            tenant_id=tenant_id, inference_service_id=inference_service_id, path=path, weight=weight, is_active=is_active
        )
        return await self.repos.inference_routes.add(route)

    async def _get_route(self, tenant_id: str, route_id: str) -> InferenceRouteModel:
        route = await self.repos.inference_routes.get(route_id)
        if route is None or route.tenant_id != tenant_id:
            raise NotFoundError(f"InferenceRoute '{route_id}' not found")
        return route

    async def set_weights(self, tenant_id: str, inference_service_id: str, *, weights: dict[str, int]) -> list[InferenceRouteModel]:
        active_total = sum(weights.values())
        if active_total != 100:
            raise InferenceError(f"Active route weights must sum to 100, got {active_total}")
        updated: list[InferenceRouteModel] = []
        for route_id, weight in weights.items():
            route = await self._get_route(tenant_id, route_id)
            if route.inference_service_id != inference_service_id:
                raise InferenceError(f"Route '{route_id}' does not belong to service '{inference_service_id}'")
            route.weight = weight
            updated.append(await self.repos.inference_routes.update(route))
        return updated

    async def deactivate_route(self, tenant_id: str, route_id: str) -> InferenceRouteModel:
        route = await self._get_route(tenant_id, route_id)
        route.is_active = False
        return await self.repos.inference_routes.update(route)

    async def activate_route(self, tenant_id: str, route_id: str) -> InferenceRouteModel:
        route = await self._get_route(tenant_id, route_id)
        route.is_active = True
        return await self.repos.inference_routes.update(route)

    async def list_for_service(self, tenant_id: str, inference_service_id: str) -> list[InferenceRouteModel]:
        return await self.repos.inference_routes.list_for_service(tenant_id, inference_service_id)

    async def list_active_for_service(self, tenant_id: str, inference_service_id: str) -> list[InferenceRouteModel]:
        routes = await self.repos.inference_routes.list_for_service(tenant_id, inference_service_id)
        return [r for r in routes if r.is_active]
