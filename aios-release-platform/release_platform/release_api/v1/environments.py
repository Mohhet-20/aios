"""Environment Management: dev/testing/QA/staging/production/sandbox/
customer-preview/enterprise-dedicated environments."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from release_platform.dependencies.dependencies import get_current_tenant_id, get_environment_service
from release_platform.environments.environment_service import EnvironmentService
from release_platform.release_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/environments", tags=["environments"])


class RegisterEnvironmentRequest(BaseModel):
    name: str
    environment_type: str
    region: str | None = None


@router.post("", status_code=201)
async def register_environment(
    body: RegisterEnvironmentRequest, tenant_id: str = Depends(get_current_tenant_id), service: EnvironmentService = Depends(get_environment_service),
):
    return to_dict(await service.register_environment(tenant_id, **body.model_dump()))


@router.get("")
async def list_environments(
    environment_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: EnvironmentService = Depends(get_environment_service),
):
    return to_dict_list(await service.list_environments(tenant_id, environment_type=environment_type))


@router.get("/{environment_id}")
async def get_environment(
    environment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: EnvironmentService = Depends(get_environment_service),
):
    return to_dict(await service.get_or_404(tenant_id, environment_id))


@router.post("/{environment_id}/activate")
async def activate_environment(
    environment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: EnvironmentService = Depends(get_environment_service),
):
    return to_dict(await service.activate(tenant_id, environment_id))


@router.post("/{environment_id}/deactivate")
async def deactivate_environment(
    environment_id: str, tenant_id: str = Depends(get_current_tenant_id), service: EnvironmentService = Depends(get_environment_service),
):
    return to_dict(await service.deactivate(tenant_id, environment_id))
