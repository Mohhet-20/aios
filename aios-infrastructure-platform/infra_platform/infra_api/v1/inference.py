"""Inference Platform API: inference service lifecycle and weighted
traffic-split routing across variants."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from infra_platform.dependencies.dependencies import get_current_tenant_id, get_inference_route_service, get_inference_service_service
from infra_platform.inference.inference_service import InferenceRouteService, InferenceServiceService
from infra_platform.infra_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/inference", tags=["inference"])


class DeployServiceRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    name: str
    model_version_id: str | None = None
    mode: str = "real_time"
    compute_type: str = "cpu"
    replicas: int = 1
    endpoint_url: str | None = None


@router.post("/services", status_code=201)
async def deploy_service(body: DeployServiceRequest, tenant_id: str = Depends(get_current_tenant_id), service: InferenceServiceService = Depends(get_inference_service_service)):
    return to_dict(await service.deploy_service(tenant_id, **body.model_dump()))


@router.get("/services")
async def list_services(tenant_id: str = Depends(get_current_tenant_id), service: InferenceServiceService = Depends(get_inference_service_service)):
    return to_dict_list(await service.list_for_tenant(tenant_id))


@router.post("/services/{service_id}/running")
async def mark_running(service_id: str, tenant_id: str = Depends(get_current_tenant_id), service: InferenceServiceService = Depends(get_inference_service_service)):
    return to_dict(await service.mark_running(tenant_id, service_id))


@router.post("/services/{service_id}/degraded")
async def mark_degraded(service_id: str, tenant_id: str = Depends(get_current_tenant_id), service: InferenceServiceService = Depends(get_inference_service_service)):
    return to_dict(await service.mark_degraded(tenant_id, service_id))


@router.post("/services/{service_id}/stop")
async def stop_service(service_id: str, tenant_id: str = Depends(get_current_tenant_id), service: InferenceServiceService = Depends(get_inference_service_service)):
    return to_dict(await service.stop(tenant_id, service_id))


@router.post("/services/{service_id}/terminate")
async def terminate_service(service_id: str, tenant_id: str = Depends(get_current_tenant_id), service: InferenceServiceService = Depends(get_inference_service_service)):
    return to_dict(await service.terminate(tenant_id, service_id))


class ScaleServiceRequest(BaseModel):
    replicas: int


@router.post("/services/{service_id}/scale")
async def scale_service(service_id: str, body: ScaleServiceRequest, tenant_id: str = Depends(get_current_tenant_id), service: InferenceServiceService = Depends(get_inference_service_service)):
    return to_dict(await service.scale(tenant_id, service_id, **body.model_dump()))


class AddRouteRequest(BaseModel):
    path: str
    weight: int = 100
    is_active: bool = True


@router.post("/services/{service_id}/routes", status_code=201)
async def add_route(service_id: str, body: AddRouteRequest, tenant_id: str = Depends(get_current_tenant_id), service: InferenceRouteService = Depends(get_inference_route_service)):
    return to_dict(await service.add_route(tenant_id, service_id, **body.model_dump()))


@router.get("/services/{service_id}/routes")
async def list_routes(service_id: str, tenant_id: str = Depends(get_current_tenant_id), service: InferenceRouteService = Depends(get_inference_route_service)):
    return to_dict_list(await service.list_for_service(tenant_id, service_id))


class SetWeightsRequest(BaseModel):
    weights: dict[str, int]


@router.put("/services/{service_id}/routes/weights")
async def set_weights(service_id: str, body: SetWeightsRequest, tenant_id: str = Depends(get_current_tenant_id), service: InferenceRouteService = Depends(get_inference_route_service)):
    return to_dict_list(await service.set_weights(tenant_id, service_id, **body.model_dump()))
