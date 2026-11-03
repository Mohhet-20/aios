"""Plugin Registry: publish a marketplace listing, ship new versions,
declare dependencies — the "list your extension" side. Installation
into a specific workspace is a separate router (`installations.py`),
mirroring the service-layer split."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tool_platform.dependencies.dependencies import get_plugin_registry_service
from tool_platform.plugin_system.registry_service import PluginRegistryService
from tool_platform.tool_api.serialization import to_dict

router = APIRouter(prefix="/plugins", tags=["plugins"])


class PublishPluginRequest(BaseModel):
    name: str
    author: str
    category: str
    slug: str | None = None
    description: str | None = None
    tags: list[str] = []
    organization_id: str | None = None
    manifest: dict = {}
    version: str = "0.1.0"


class PublishVersionRequest(BaseModel):
    version: str
    manifest: dict | None = None


class AddDependencyRequest(BaseModel):
    depends_on_plugin_id: str
    version_constraint: str = "*"


@router.post("", status_code=201)
async def publish_plugin(body: PublishPluginRequest, svc: PluginRegistryService = Depends(get_plugin_registry_service)):
    return to_dict(await svc.publish_plugin(
        name=body.name, author=body.author, category=body.category, slug=body.slug, description=body.description,
        tags=body.tags, organization_id=body.organization_id, manifest=body.manifest, version=body.version,
    ))


@router.get("/{plugin_id}")
async def get_plugin(plugin_id: str, svc: PluginRegistryService = Depends(get_plugin_registry_service)):
    return to_dict(await svc.get_plugin(plugin_id))


@router.post("/{plugin_id}/versions", status_code=201)
async def publish_new_version(plugin_id: str, body: PublishVersionRequest, svc: PluginRegistryService = Depends(get_plugin_registry_service)):
    return to_dict(await svc.publish_new_version(plugin_id, version=body.version, manifest=body.manifest))


@router.post("/{plugin_id}/dependencies", status_code=201)
async def add_dependency(plugin_id: str, body: AddDependencyRequest, svc: PluginRegistryService = Depends(get_plugin_registry_service)):
    return to_dict(await svc.add_dependency(plugin_id, depends_on_plugin_id=body.depends_on_plugin_id, version_constraint=body.version_constraint))


@router.post("/{plugin_id}/deprecate")
async def deprecate_plugin(plugin_id: str, svc: PluginRegistryService = Depends(get_plugin_registry_service)):
    return to_dict(await svc.deprecate_plugin(plugin_id))


@router.post("/{plugin_id}/suspend")
async def suspend_plugin(plugin_id: str, reason: str, svc: PluginRegistryService = Depends(get_plugin_registry_service)):
    return to_dict(await svc.suspend_plugin(plugin_id, reason=reason))
