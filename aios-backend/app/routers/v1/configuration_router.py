from fastapi import APIRouter, Depends

from app.dependencies.auth_dependencies import require_permission
from app.dependencies.service_dependencies import get_configuration_service
from app.schemas.configuration import ConfigurationRead, ConfigurationSetRequest
from app.security.permissions import Permission
from app.services.configuration_service import ConfigurationService

router = APIRouter(prefix="/configuration", tags=["Configuration"])


@router.get("/{organization_id}/{key}", response_model=ConfigurationRead)
async def get_configuration(
    organization_id: str, key: str, service: ConfigurationService = Depends(get_configuration_service)
):
    value = await service.get(organization_id, key)
    return ConfigurationRead(key=key, value=value)


@router.put("/{organization_id}", response_model=ConfigurationRead)
async def set_configuration(
    organization_id: str,
    payload: ConfigurationSetRequest,
    service: ConfigurationService = Depends(get_configuration_service),
    _principal=Depends(require_permission(Permission.CONFIGURATION_MANAGE)),
):
    await service.set(organization_id, payload.key, payload.value)
    return ConfigurationRead(key=payload.key, value=payload.value)
