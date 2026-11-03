"""Versioned Documentation: read-side access to page content
snapshots and diffs, release notes grouped by version label, and
deprecation notices."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from docs_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_deprecation_service,
    get_doc_version_service,
    get_release_note_service,
)
from docs_platform.doc_api.serialization import to_dict, to_dict_list
from docs_platform.versioning.deprecation_service import DeprecationService
from docs_platform.versioning.release_note_service import ReleaseNoteService
from docs_platform.versioning.version_service import DocVersionService

router = APIRouter(prefix="/doc-versions", tags=["versioning"])
release_notes_router = APIRouter(prefix="/release-notes", tags=["versioning"])
deprecations_router = APIRouter(prefix="/deprecation-notices", tags=["versioning"])


@router.get("/{page_id}")
async def list_versions(
    page_id: str, tenant_id: str = Depends(get_current_tenant_id), service: DocVersionService = Depends(get_doc_version_service),
):
    return to_dict_list(await service.list_versions(tenant_id, page_id))


@router.get("/{page_id}/{version_number}")
async def get_version(
    page_id: str, version_number: int, tenant_id: str = Depends(get_current_tenant_id), service: DocVersionService = Depends(get_doc_version_service),
):
    return to_dict(await service.get_version(tenant_id, page_id, version_number))


@router.get("/{page_id}/diff/{from_version}/{to_version}")
async def diff_versions(
    page_id: str, from_version: int, to_version: int,
    tenant_id: str = Depends(get_current_tenant_id), service: DocVersionService = Depends(get_doc_version_service),
):
    lines = await service.diff(tenant_id, page_id, from_version=from_version, to_version=to_version)
    return {"diff": lines}


class CreateReleaseNoteRequest(BaseModel):
    version_label: str
    title: str
    content: str = ""
    kind: str = "feature"


@release_notes_router.post("", status_code=201)
async def create_release_note(
    body: CreateReleaseNoteRequest, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseNoteService = Depends(get_release_note_service),
):
    return to_dict(await service.create_note(tenant_id, **body.model_dump()))


@release_notes_router.get("")
async def list_release_notes(
    version_label: str | None = None, limit: int = 100,
    tenant_id: str = Depends(get_current_tenant_id), service: ReleaseNoteService = Depends(get_release_note_service),
):
    return to_dict_list(await service.list_notes(tenant_id, version_label=version_label, limit=limit))


class CreateDeprecationNoticeRequest(BaseModel):
    subject_ref: str
    message: str
    removal_at: datetime | None = None


@deprecations_router.post("", status_code=201)
async def create_deprecation_notice(
    body: CreateDeprecationNoticeRequest, tenant_id: str = Depends(get_current_tenant_id), service: DeprecationService = Depends(get_deprecation_service),
):
    return to_dict(await service.create_notice(tenant_id, **body.model_dump()))


@deprecations_router.get("")
async def list_deprecation_notices(
    limit: int = 100, tenant_id: str = Depends(get_current_tenant_id), service: DeprecationService = Depends(get_deprecation_service),
):
    return to_dict_list(await service.list_notices(tenant_id, limit=limit))
