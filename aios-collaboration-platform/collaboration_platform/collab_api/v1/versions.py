"""Version history: create/list/compare/rollback/releases, branches,
and merges."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from collaboration_platform.collab_api.serialization import to_dict, to_dict_list
from collaboration_platform.dependencies.dependencies import get_branch_service, get_merge_service, get_version_service
from collaboration_platform.domain.enums import MergeStrategy
from collaboration_platform.versioning.branch_service import BranchService
from collaboration_platform.versioning.merge_service import MergeService
from collaboration_platform.versioning.version_service import VersionService

router = APIRouter(prefix="/versions", tags=["versions"])


class CreateVersionRequest(BaseModel):
    asset_id: str
    created_by: str
    content_snapshot: dict
    branch_name: str = "main"
    change_summary: str | None = None
    expected_base_version_id: str | None = "__skip__"
    is_release: bool = False
    release_tag: str | None = None


@router.post("", status_code=201)
async def create_version(body: CreateVersionRequest, service: VersionService = Depends(get_version_service)):
    return to_dict(await service.create_version(
        body.asset_id, body.created_by, body.content_snapshot, branch_name=body.branch_name, change_summary=body.change_summary,
        expected_base_version_id=body.expected_base_version_id, is_release=body.is_release, release_tag=body.release_tag,
    ))


@router.get("/asset/{asset_id}")
async def list_versions(asset_id: str, branch_name: str | None = None, service: VersionService = Depends(get_version_service)):
    return to_dict_list(await service.list_versions(asset_id, branch_name=branch_name))


@router.get("/asset/{asset_id}/latest")
async def get_latest(asset_id: str, branch_name: str = "main", service: VersionService = Depends(get_version_service)):
    return to_dict(await service.get_latest(asset_id, branch_name=branch_name))


@router.get("/asset/{asset_id}/releases")
async def list_releases(asset_id: str, service: VersionService = Depends(get_version_service)):
    return to_dict_list(await service.list_releases(asset_id))


@router.get("/compare/{version_id_a}/{version_id_b}")
async def compare_versions(version_id_a: str, version_id_b: str, service: VersionService = Depends(get_version_service)):
    return await service.compare(version_id_a, version_id_b)


class RollbackRequest(BaseModel):
    target_version_id: str
    created_by: str
    branch_name: str = "main"


@router.post("/asset/{asset_id}/rollback")
async def rollback(asset_id: str, body: RollbackRequest, service: VersionService = Depends(get_version_service)):
    return to_dict(await service.rollback(asset_id, body.target_version_id, created_by=body.created_by, branch_name=body.branch_name))


branches_router = APIRouter(prefix="/branches", tags=["versions"])


class CreateBranchRequest(BaseModel):
    asset_id: str
    name: str
    created_by: str
    base_version_id: str | None = None


@branches_router.post("", status_code=201)
async def create_branch(body: CreateBranchRequest, service: BranchService = Depends(get_branch_service)):
    return to_dict(await service.create_branch(body.asset_id, name=body.name, created_by=body.created_by, base_version_id=body.base_version_id))


@branches_router.get("/asset/{asset_id}")
async def list_branches(asset_id: str, service: BranchService = Depends(get_branch_service)):
    return to_dict_list(await service.list_for_asset(asset_id))


@branches_router.post("/{branch_id}/close")
async def close_branch(branch_id: str, service: BranchService = Depends(get_branch_service)):
    return to_dict(await service.close(branch_id))


class MergeRequest(BaseModel):
    target_branch_name: str
    merged_by: str
    strategy: MergeStrategy = MergeStrategy.FAST_FORWARD
    manual_content: dict | None = None


@branches_router.post("/{branch_id}/merge", status_code=201)
async def merge_branch(branch_id: str, body: MergeRequest, service: MergeService = Depends(get_merge_service)):
    return to_dict(await service.merge(
        branch_id, target_branch_name=body.target_branch_name, merged_by=body.merged_by, strategy=body.strategy, manual_content=body.manual_content,
    ))


@branches_router.get("/{branch_id}/merges")
async def list_merges(branch_id: str, service: MergeService = Depends(get_merge_service)):
    return to_dict_list(await service.list_for_branch(branch_id))
