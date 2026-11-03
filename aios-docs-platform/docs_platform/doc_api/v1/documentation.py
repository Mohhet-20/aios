"""Documentation Core: doc spaces and pages across the 15 doc types."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from docs_platform.dependencies.dependencies import get_current_tenant_id, get_doc_page_service, get_doc_space_service
from docs_platform.doc_api.serialization import to_dict, to_dict_list
from docs_platform.documentation.doc_page_service import DocPageService
from docs_platform.documentation.doc_space_service import DocSpaceService

router = APIRouter(prefix="/doc-spaces", tags=["documentation"])
pages_router = APIRouter(prefix="/doc-pages", tags=["documentation"])


class RegisterSpaceRequest(BaseModel):
    key: str
    name: str
    doc_type: str
    description: str | None = None


@router.post("", status_code=201)
async def register_space(
    body: RegisterSpaceRequest, tenant_id: str = Depends(get_current_tenant_id), service: DocSpaceService = Depends(get_doc_space_service),
):
    return to_dict(await service.register_space(tenant_id, **body.model_dump()))


@router.get("")
async def list_spaces(
    doc_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: DocSpaceService = Depends(get_doc_space_service),
):
    return to_dict_list(await service.list_spaces(tenant_id, doc_type=doc_type))


@router.get("/{space_id}")
async def get_space(
    space_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DocSpaceService = Depends(get_doc_space_service),
):
    return to_dict(await service.get_or_404(tenant_id, space_id))


@router.get("/{space_id}/pages")
async def list_pages_for_space(
    space_id: str, status: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: DocPageService = Depends(get_doc_page_service),
):
    return to_dict_list(await service.list_for_space(tenant_id, space_id, status=status))


class CreatePageRequest(BaseModel):
    space_id: str
    title: str
    slug: str
    doc_type: str
    content: str = ""
    owner_id: str | None = None
    visibility: str | None = None


@pages_router.post("", status_code=201)
async def create_page(
    body: CreatePageRequest, tenant_id: str = Depends(get_current_tenant_id), service: DocPageService = Depends(get_doc_page_service),
):
    payload = body.model_dump()
    space_id = payload.pop("space_id")
    return to_dict(await service.create_page(tenant_id, space_id, **payload))


@pages_router.get("")
async def list_pages(
    doc_type: str | None = None, status: str | None = None,
    tenant_id: str = Depends(get_current_tenant_id), service: DocPageService = Depends(get_doc_page_service),
):
    return to_dict_list(await service.list_pages(tenant_id, doc_type=doc_type, status=status))


@pages_router.get("/{page_id}")
async def get_page(
    page_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DocPageService = Depends(get_doc_page_service),
):
    return to_dict(await service.get_or_404(tenant_id, page_id))


class UpdateContentRequest(BaseModel):
    content: str
    actor_id: str | None = None


@pages_router.put("/{page_id}/content")
async def update_content(
    page_id: str, body: UpdateContentRequest, tenant_id: str = Depends(get_current_tenant_id), service: DocPageService = Depends(get_doc_page_service),
):
    return to_dict(await service.update_content(tenant_id, page_id, **body.model_dump()))


@pages_router.post("/{page_id}/submit-for-review")
async def submit_for_review(
    page_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DocPageService = Depends(get_doc_page_service),
):
    return to_dict(await service.submit_for_review(tenant_id, page_id))


@pages_router.post("/{page_id}/publish")
async def publish_page(
    page_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DocPageService = Depends(get_doc_page_service),
):
    return to_dict(await service.publish(tenant_id, page_id))


@pages_router.post("/{page_id}/reject")
async def reject_page(
    page_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DocPageService = Depends(get_doc_page_service),
):
    return to_dict(await service.reject(tenant_id, page_id))


@pages_router.post("/{page_id}/archive")
async def archive_page(
    page_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DocPageService = Depends(get_doc_page_service),
):
    return to_dict(await service.archive(tenant_id, page_id))


@pages_router.post("/{page_id}/deprecate")
async def deprecate_page(
    page_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DocPageService = Depends(get_doc_page_service),
):
    return to_dict(await service.deprecate(tenant_id, page_id))
