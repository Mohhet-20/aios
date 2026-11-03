from fastapi import APIRouter, Depends, status

from app.dependencies.auth_dependencies import require_permission
from app.dependencies.service_dependencies import get_plugin_service
from app.schemas.plugin import PluginInstallRequest, PluginManifestRead, PluginRead
from app.security.permissions import Permission
from app.services.plugin_service import PluginService

router = APIRouter(prefix="/plugins", tags=["Plugins"])


@router.get("/available", response_model=list[PluginManifestRead])
async def list_available_plugins(service: PluginService = Depends(get_plugin_service)):
    return [
        PluginManifestRead(
            id=m.id,
            name=m.name,
            version=m.version,
            category=m.category,
            description=m.description,
            provides_tools=m.provides_tools,
            provides_graders=m.provides_graders,
        )
        for m in service.list_available()
    ]


@router.get("", response_model=list[PluginRead])
async def list_installed_plugins(organization_id: str, service: PluginService = Depends(get_plugin_service)):
    return await service.list_installed(organization_id)


@router.post("/{organization_id}/install", response_model=PluginRead, status_code=status.HTTP_201_CREATED)
async def install_plugin(
    organization_id: str,
    payload: PluginInstallRequest,
    service: PluginService = Depends(get_plugin_service),
    _principal=Depends(require_permission(Permission.PLUGIN_MANAGE)),
):
    return await service.install(organization_id, payload.plugin_manifest_id)


@router.post("/{plugin_id}/toggle", response_model=PluginRead)
async def toggle_plugin(
    plugin_id: str,
    enabled: bool,
    service: PluginService = Depends(get_plugin_service),
    _principal=Depends(require_permission(Permission.PLUGIN_MANAGE)),
):
    return await service.toggle(plugin_id, enabled)
