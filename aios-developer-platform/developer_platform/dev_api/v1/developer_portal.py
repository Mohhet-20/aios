"""Developer Portal content pages and ephemeral sandbox environments."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from developer_platform.dependencies.dependencies import get_current_tenant_id, get_portal_content_service, get_sandbox_service
from developer_platform.developer_portal.content_service import PortalContentService
from developer_platform.developer_portal.sandbox_service import SandboxService
from developer_platform.dev_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/portal/content", tags=["developer-portal"])


class CreateContentRequest(BaseModel):
    content_type: str
    slug: str
    title: str
    body: str = ""


@router.post("", status_code=201)
async def create_portal_content(
    body: CreateContentRequest, tenant_id: str = Depends(get_current_tenant_id), service: PortalContentService = Depends(get_portal_content_service),
):
    return to_dict(await service.create_content(tenant_id, **body.model_dump()))


class UpdateContentRequest(BaseModel):
    title: str | None = None
    body: str | None = None


@router.patch("/{content_id}")
async def update_portal_content(
    content_id: str, body: UpdateContentRequest, service: PortalContentService = Depends(get_portal_content_service),
):
    return to_dict(await service.update_content(content_id, **body.model_dump()))


@router.post("/{content_id}/publish")
async def publish_portal_content(content_id: str, service: PortalContentService = Depends(get_portal_content_service)):
    return to_dict(await service.publish(content_id))


@router.post("/{content_id}/archive")
async def archive_portal_content(content_id: str, service: PortalContentService = Depends(get_portal_content_service)):
    return to_dict(await service.archive(content_id))


@router.get("/{content_type}/{slug}")
async def get_portal_content_by_slug(
    content_type: str, slug: str, tenant_id: str = Depends(get_current_tenant_id), service: PortalContentService = Depends(get_portal_content_service),
):
    return to_dict(await service.get_by_slug(tenant_id, content_type, slug))


@router.get("/{content_type}")
async def list_portal_content_by_type(
    content_type: str, tenant_id: str = Depends(get_current_tenant_id), service: PortalContentService = Depends(get_portal_content_service),
):
    return to_dict_list(await service.list_by_type(tenant_id, content_type))


@router.get("")
async def list_published_portal_content(
    tenant_id: str = Depends(get_current_tenant_id), service: PortalContentService = Depends(get_portal_content_service),
):
    return to_dict_list(await service.list_published(tenant_id))


sandbox_router = APIRouter(prefix="/portal/sandboxes", tags=["developer-portal"])


class ProvisionSandboxRequest(BaseModel):
    developer_id: str


@sandbox_router.post("", status_code=201)
async def provision_sandbox(
    body: ProvisionSandboxRequest, tenant_id: str = Depends(get_current_tenant_id), service: SandboxService = Depends(get_sandbox_service),
):
    return to_dict(await service.provision(tenant_id, body.developer_id))


@sandbox_router.post("/{sandbox_id}/mark-running")
async def mark_sandbox_running(sandbox_id: str, service: SandboxService = Depends(get_sandbox_service)):
    return to_dict(await service.mark_running(sandbox_id))


@sandbox_router.post("/{sandbox_id}/terminate")
async def terminate_sandbox(sandbox_id: str, service: SandboxService = Depends(get_sandbox_service)):
    return to_dict(await service.terminate(sandbox_id))


@sandbox_router.get("/for-developer/{developer_id}")
async def list_sandboxes_for_developer(
    developer_id: str, tenant_id: str = Depends(get_current_tenant_id), service: SandboxService = Depends(get_sandbox_service),
):
    return to_dict_list(await service.list_for_developer(tenant_id, developer_id))
