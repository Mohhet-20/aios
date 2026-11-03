"""Service Mesh: service discovery/registry, load balancing, circuit
breakers, health checks."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from gateway_platform.dependencies.dependencies import (
    get_circuit_breaker_service,
    get_current_tenant_id,
    get_health_check_service,
    get_load_balancer_service,
    get_service_registry_service,
)
from gateway_platform.domain.enums import InstanceStatus
from gateway_platform.gw_api.serialization import to_dict, to_dict_list
from gateway_platform.service_mesh.circuit_breaker_service import CircuitBreakerService
from gateway_platform.service_mesh.health_check_service import HealthCheckService
from gateway_platform.service_mesh.load_balancer_service import LoadBalancerService
from gateway_platform.service_mesh.registry_service import ServiceRegistryService

router = APIRouter(prefix="/mesh/services", tags=["service-mesh"])


class RegisterServiceRequest(BaseModel):
    name: str
    metadata: dict | None = None


@router.post("", status_code=201)
async def register_service(
    body: RegisterServiceRequest, tenant_id: str = Depends(get_current_tenant_id), service: ServiceRegistryService = Depends(get_service_registry_service),
):
    return to_dict(await service.register_service(tenant_id, **body.model_dump()))


@router.get("")
async def list_services(tenant_id: str = Depends(get_current_tenant_id), service: ServiceRegistryService = Depends(get_service_registry_service)):
    return to_dict_list(await service.list_services(tenant_id))


@router.post("/{service_id}/mark-healthy")
async def mark_service_healthy(
    service_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ServiceRegistryService = Depends(get_service_registry_service),
):
    return to_dict(await service.mark_healthy(tenant_id, service_id))


@router.post("/{service_id}/mark-unhealthy")
async def mark_service_unhealthy(
    service_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ServiceRegistryService = Depends(get_service_registry_service),
):
    return to_dict(await service.mark_unhealthy(tenant_id, service_id))


@router.post("/{service_id}/deregister")
async def deregister_service(
    service_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ServiceRegistryService = Depends(get_service_registry_service),
):
    return to_dict(await service.deregister_service(tenant_id, service_id))


class RegisterInstanceRequest(BaseModel):
    host: str
    port: int = 80
    weight: int = 1


@router.post("/{service_id}/instances", status_code=201)
async def register_instance(
    service_id: str, body: RegisterInstanceRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: ServiceRegistryService = Depends(get_service_registry_service),
):
    return to_dict(await service.register_instance(tenant_id, service_id, **body.model_dump()))


@router.get("/{service_id}/instances")
async def list_instances(
    service_id: str, status: str | None = None, tenant_id: str = Depends(get_current_tenant_id),
    service: ServiceRegistryService = Depends(get_service_registry_service),
):
    return to_dict_list(await service.list_instances(tenant_id, service_id, status=status))


class TransitionInstanceRequest(BaseModel):
    target: str


@router.post("/instances/{instance_id}/transition")
async def transition_instance(
    instance_id: str, body: TransitionInstanceRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: ServiceRegistryService = Depends(get_service_registry_service),
):
    return to_dict(await service.transition_instance(tenant_id, instance_id, InstanceStatus(body.target)))


load_balancer_router = APIRouter(prefix="/mesh/load-balancer", tags=["service-mesh"])


class ConfigurePoolRequest(BaseModel):
    strategy: str | None = None


@load_balancer_router.post("/{service_id}/configure")
async def configure_pool(
    service_id: str, body: ConfigurePoolRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: LoadBalancerService = Depends(get_load_balancer_service),
):
    return to_dict(await service.configure_pool(tenant_id, service_id, strategy=body.strategy))


@load_balancer_router.get("/{service_id}/select")
async def select_instance(
    service_id: str, tenant_id: str = Depends(get_current_tenant_id), service: LoadBalancerService = Depends(get_load_balancer_service),
):
    return to_dict(await service.select_instance(tenant_id, service_id))


circuit_breaker_router = APIRouter(prefix="/mesh/circuit-breakers", tags=["service-mesh"])


@circuit_breaker_router.get("/{service_id}")
async def get_circuit_breaker(
    service_id: str, tenant_id: str = Depends(get_current_tenant_id), service: CircuitBreakerService = Depends(get_circuit_breaker_service),
):
    return to_dict(await service.get_or_create(tenant_id, service_id))


@circuit_breaker_router.post("/{service_id}/enforce")
async def enforce_circuit_breaker(
    service_id: str, tenant_id: str = Depends(get_current_tenant_id), service: CircuitBreakerService = Depends(get_circuit_breaker_service),
):
    return to_dict(await service.enforce(tenant_id, service_id))


@circuit_breaker_router.post("/{service_id}/record-success")
async def record_circuit_breaker_success(
    service_id: str, tenant_id: str = Depends(get_current_tenant_id), service: CircuitBreakerService = Depends(get_circuit_breaker_service),
):
    return to_dict(await service.record_success(tenant_id, service_id))


@circuit_breaker_router.post("/{service_id}/record-failure")
async def record_circuit_breaker_failure(
    service_id: str, tenant_id: str = Depends(get_current_tenant_id), service: CircuitBreakerService = Depends(get_circuit_breaker_service),
):
    return to_dict(await service.record_failure(tenant_id, service_id))


health_router = APIRouter(prefix="/mesh/health-checks", tags=["service-mesh"])


class RecordHealthCheckRequest(BaseModel):
    healthy: bool
    latency_ms: float = 0.0


@health_router.post("/{instance_id}")
async def record_health_check(
    instance_id: str, body: RecordHealthCheckRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: HealthCheckService = Depends(get_health_check_service),
):
    return to_dict(await service.record_result(tenant_id, instance_id, **body.model_dump()))


@health_router.get("/{instance_id}")
async def list_health_checks(
    instance_id: str, tenant_id: str = Depends(get_current_tenant_id), service: HealthCheckService = Depends(get_health_check_service),
):
    return to_dict_list(await service.list_for_instance(tenant_id, instance_id))
