"""Component registry + health monitoring API. Two sub-routers:
`components_router` manages what's registered as observable,
`health_router` manages the health-check results and derived rollups."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from observability_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_health_aggregation_service,
    get_healthcheck_service,
    get_repos,
)
from observability_platform.health.aggregation_service import HealthAggregationService
from observability_platform.health.healthcheck_service import HealthCheckService
from observability_platform.models.components import ComponentModel
from observability_platform.obs_api.serialization import to_dict, to_dict_list
from observability_platform.repositories.registry import RepositoryRegistry

components_router = APIRouter(prefix="/components", tags=["components"])


class RegisterComponentRequest(BaseModel):
    name: str
    component_type: str
    description: str | None = None
    owner_team: str | None = None


@components_router.post("", status_code=201)
async def register_component(
    body: RegisterComponentRequest, tenant_id: str = Depends(get_current_tenant_id), repos: RepositoryRegistry = Depends(get_repos)
):
    component = ComponentModel(tenant_id=tenant_id, **body.model_dump())
    return to_dict(await repos.components.add(component))


@components_router.get("")
async def list_components(
    tenant_id: str = Depends(get_current_tenant_id), component_type: str | None = None, repos: RepositoryRegistry = Depends(get_repos)
):
    return to_dict_list(await repos.components.list_for_tenant(tenant_id, component_type=component_type))


@components_router.get("/{component_id}")
async def get_component(component_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict(await repos.components.get_or_404(component_id))


health_router = APIRouter(prefix="/health", tags=["health"])


class RecordHealthResultRequest(BaseModel):
    status: str
    message: str | None = None
    latency_ms: float | None = None
    metadata: dict | None = None


@health_router.post("/components/{component_id}/results", status_code=201)
async def record_health_result(
    component_id: str, body: RecordHealthResultRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: HealthCheckService = Depends(get_healthcheck_service),
):
    return to_dict(await service.record_result(tenant_id, component_id, **body.model_dump()))


@health_router.get("/components/{component_id}/status")
async def component_status(
    component_id: str, tenant_id: str = Depends(get_current_tenant_id), service: HealthCheckService = Depends(get_healthcheck_service)
):
    return {"status": (await service.current_status(tenant_id, component_id)).value}


@health_router.get("/components/{component_id}/history")
async def component_history(
    component_id: str, tenant_id: str = Depends(get_current_tenant_id), limit: int = 100,
    service: HealthCheckService = Depends(get_healthcheck_service),
):
    return to_dict_list(await service.history(tenant_id, component_id, limit=limit))


@health_router.get("/overall")
async def overall_health(tenant_id: str = Depends(get_current_tenant_id), service: HealthAggregationService = Depends(get_health_aggregation_service)):
    return await service.overall_system_health(tenant_id)


@health_router.get("/by-component-type")
async def health_by_type(tenant_id: str = Depends(get_current_tenant_id), service: HealthAggregationService = Depends(get_health_aggregation_service)):
    return await service.health_by_component_type(tenant_id)
