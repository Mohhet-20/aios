"""API / SDK Documentation & Automation: REST/GraphQL/WebSocket/
Streaming API doc entries, per-language SDK doc entries, and the
generation job lifecycle that backs automated doc generation."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from docs_platform.automation.generation_job_service import GenerationJobService
from docs_platform.api_docs.api_doc_service import ApiDocService
from docs_platform.dependencies.dependencies import (
    get_api_doc_service,
    get_current_tenant_id,
    get_generation_job_service,
    get_sdk_doc_service,
)
from docs_platform.doc_api.serialization import to_dict, to_dict_list
from docs_platform.sdk_docs.sdk_doc_service import SdkDocService

router = APIRouter(prefix="/api-docs", tags=["api-docs"])
sdk_router = APIRouter(prefix="/sdk-docs", tags=["sdk-docs"])
jobs_router = APIRouter(prefix="/generation-jobs", tags=["automation"])


class CreateApiDocEntryRequest(BaseModel):
    protocol_type: str
    path: str
    method: str | None = None
    summary: str = ""
    request_example: dict | None = None
    response_example: dict | None = None
    auth_example: str = ""
    error_docs: list | None = None
    version: str = "v1"


@router.post("", status_code=201)
async def create_api_doc_entry(
    body: CreateApiDocEntryRequest, tenant_id: str = Depends(get_current_tenant_id), service: ApiDocService = Depends(get_api_doc_service),
):
    return to_dict(await service.create_entry(tenant_id, **body.model_dump()))


@router.get("")
async def list_api_doc_entries(
    protocol_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: ApiDocService = Depends(get_api_doc_service),
):
    return to_dict_list(await service.list_entries(tenant_id, protocol_type=protocol_type))


@router.get("/{entry_id}")
async def get_api_doc_entry(
    entry_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ApiDocService = Depends(get_api_doc_service),
):
    return to_dict(await service.get_or_404(tenant_id, entry_id))


class CreateSdkDocEntryRequest(BaseModel):
    sdk_language: str
    package_ref: str
    title: str
    content: str = ""
    version: str = "v1"


@sdk_router.post("", status_code=201)
async def create_sdk_doc_entry(
    body: CreateSdkDocEntryRequest, tenant_id: str = Depends(get_current_tenant_id), service: SdkDocService = Depends(get_sdk_doc_service),
):
    return to_dict(await service.create_entry(tenant_id, **body.model_dump()))


@sdk_router.get("")
async def list_sdk_doc_entries(
    tenant_id: str = Depends(get_current_tenant_id), service: SdkDocService = Depends(get_sdk_doc_service),
):
    return to_dict_list(await service.list_entries(tenant_id))


@sdk_router.get("/by-language/{sdk_language}")
async def list_sdk_doc_entries_for_language(
    sdk_language: str, tenant_id: str = Depends(get_current_tenant_id), service: SdkDocService = Depends(get_sdk_doc_service),
):
    return to_dict_list(await service.list_for_language(tenant_id, sdk_language))


@sdk_router.get("/{entry_id}")
async def get_sdk_doc_entry(
    entry_id: str, tenant_id: str = Depends(get_current_tenant_id), service: SdkDocService = Depends(get_sdk_doc_service),
):
    return to_dict(await service.get_or_404(tenant_id, entry_id))


class RequestJobRequest(BaseModel):
    job_type: str
    target_ref: str
    config: dict | None = None


@jobs_router.post("", status_code=201)
async def request_job(
    body: RequestJobRequest, tenant_id: str = Depends(get_current_tenant_id), service: GenerationJobService = Depends(get_generation_job_service),
):
    return to_dict(await service.request_job(tenant_id, **body.model_dump()))


@jobs_router.get("/{job_id}")
async def get_job(
    job_id: str, tenant_id: str = Depends(get_current_tenant_id), service: GenerationJobService = Depends(get_generation_job_service),
):
    return to_dict(await service.get_or_404(tenant_id, job_id))


@jobs_router.post("/{job_id}/run")
async def run_job(
    job_id: str, tenant_id: str = Depends(get_current_tenant_id), service: GenerationJobService = Depends(get_generation_job_service),
):
    # No generator callable is supplied through the HTTP surface — this
    # runs the honest "no generator function supplied" path documented
    # on GenerationJobService.run_job rather than pretending to
    # introspect a live codebase over HTTP.
    return to_dict(await service.run_job(tenant_id, job_id))


@jobs_router.get("")
async def list_jobs(
    job_type: str | None = None, limit: int = 100,
    tenant_id: str = Depends(get_current_tenant_id), service: GenerationJobService = Depends(get_generation_job_service),
):
    return to_dict_list(await service.list_jobs(tenant_id, job_type=job_type, limit=limit))
