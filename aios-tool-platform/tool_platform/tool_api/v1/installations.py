"""Plugin Installation: a specific workspace's copy of a marketplace
plugin — install (signature + dependency + isolation checks), enable/
disable/update/uninstall. The "Plugin Manager" frontend surface."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tool_platform.dependencies.dependencies import get_plugin_installation_service
from tool_platform.plugin_system.installation_service import PluginInstallationService
from tool_platform.tool_api.serialization import to_dict

router = APIRouter(prefix="/installations", tags=["plugin_installations"])


class InstallPluginRequest(BaseModel):
    workspace_id: str
    plugin_id: str
    installed_by: str
    configuration: dict = {}
    workspace_allowed_capabilities: list[str] | None = None


class CompleteUpdateRequest(BaseModel):
    new_version: str


class FailUpdateRequest(BaseModel):
    error_message: str


@router.post("", status_code=201)
async def install_plugin(body: InstallPluginRequest, svc: PluginInstallationService = Depends(get_plugin_installation_service)):
    return to_dict(await svc.install(
        body.workspace_id, body.plugin_id, installed_by=body.installed_by, configuration=body.configuration,
        workspace_allowed_capabilities=body.workspace_allowed_capabilities,
    ))


@router.post("/{installation_id}/enable")
async def enable_installation(installation_id: str, svc: PluginInstallationService = Depends(get_plugin_installation_service)):
    return to_dict(await svc.enable(installation_id))


@router.post("/{installation_id}/disable")
async def disable_installation(installation_id: str, svc: PluginInstallationService = Depends(get_plugin_installation_service)):
    return to_dict(await svc.disable(installation_id))


@router.post("/{installation_id}/uninstall")
async def uninstall(installation_id: str, svc: PluginInstallationService = Depends(get_plugin_installation_service)):
    return to_dict(await svc.uninstall(installation_id))


@router.post("/{installation_id}/update/begin")
async def begin_update(installation_id: str, svc: PluginInstallationService = Depends(get_plugin_installation_service)):
    return to_dict(await svc.begin_update(installation_id))


@router.post("/{installation_id}/update/complete")
async def complete_update(installation_id: str, body: CompleteUpdateRequest, svc: PluginInstallationService = Depends(get_plugin_installation_service)):
    return to_dict(await svc.complete_update(installation_id, new_version=body.new_version))


@router.post("/{installation_id}/update/fail")
async def fail_update(installation_id: str, body: FailUpdateRequest, svc: PluginInstallationService = Depends(get_plugin_installation_service)):
    return to_dict(await svc.fail_update(installation_id, error_message=body.error_message))
