"""Prompt Version control: create/submit/approve/reject/promote/rollback,
diff, and history — the version-management surface of Prompt Versioning."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from prompt_platform.domain.enums import VersionBranch
from prompt_platform.prompt_api.dependencies import get_current_actor_id, get_repos, get_versioning_service
from prompt_platform.prompt_api.serialization import to_dict, to_dict_list
from prompt_platform.prompt_engine.versioning_service import VersioningService
from prompt_platform.repositories.registry import RepositoryRegistry

router = APIRouter(prefix="/prompts/{prompt_id}/versions", tags=["versions"])


class CreateVersionRequest(BaseModel):
    user_template: str
    system_template: str | None = None
    developer_template: str | None = None
    variables_schema: list[dict] | None = None
    parameters: dict | None = None
    parent_version_id: str | None = None


class RejectVersionRequest(BaseModel):
    reason: str


class PromoteVersionRequest(BaseModel):
    target_branch: VersionBranch
    release_notes: str | None = None


class RollbackRequest(BaseModel):
    reason: str | None = None


@router.post("", status_code=201)
async def create_version(prompt_id: str, body: CreateVersionRequest, actor_id: str = Depends(get_current_actor_id), svc: VersioningService = Depends(get_versioning_service)):
    version = await svc.create_version(
        prompt_id, user_template=body.user_template, actor_id=actor_id, system_template=body.system_template,
        developer_template=body.developer_template, variables_schema=body.variables_schema, parameters=body.parameters,
        parent_version_id=body.parent_version_id,
    )
    return to_dict(version)


@router.get("")
async def list_versions(prompt_id: str, svc: VersioningService = Depends(get_versioning_service)):
    return to_dict_list(await svc.list_versions(prompt_id))


@router.get("/{version_id}")
async def get_version(prompt_id: str, version_id: str, repos: RepositoryRegistry = Depends(get_repos)):
    return to_dict(await repos.versions.get_or_404(version_id))


@router.post("/{version_id}/submit-for-review")
async def submit_for_review(prompt_id: str, version_id: str, actor_id: str = Depends(get_current_actor_id), svc: VersioningService = Depends(get_versioning_service)):
    return to_dict(await svc.submit_for_review(version_id, actor_id))


@router.post("/{version_id}/approve")
async def approve_version(prompt_id: str, version_id: str, actor_id: str = Depends(get_current_actor_id), svc: VersioningService = Depends(get_versioning_service)):
    return to_dict(await svc.approve(version_id, actor_id))


@router.post("/{version_id}/reject")
async def reject_version(prompt_id: str, version_id: str, body: RejectVersionRequest, actor_id: str = Depends(get_current_actor_id), svc: VersioningService = Depends(get_versioning_service)):
    return to_dict(await svc.reject(version_id, actor_id, body.reason))


@router.post("/{version_id}/promote")
async def promote_version(prompt_id: str, version_id: str, body: PromoteVersionRequest, actor_id: str = Depends(get_current_actor_id), svc: VersioningService = Depends(get_versioning_service)):
    return to_dict(await svc.promote(prompt_id, version_id, body.target_branch, actor_id, release_notes=body.release_notes))


@router.post("/{version_id}/rollback")
async def rollback_version(prompt_id: str, version_id: str, body: RollbackRequest, actor_id: str = Depends(get_current_actor_id), svc: VersioningService = Depends(get_versioning_service)):
    return to_dict(await svc.rollback(prompt_id, version_id, actor_id, reason=body.reason))


@router.get("/diff/{version_id_a}/{version_id_b}")
async def diff_versions(prompt_id: str, version_id_a: str, version_id_b: str, svc: VersioningService = Depends(get_versioning_service)):
    return await svc.diff_versions(version_id_a, version_id_b)


@router.get("/history/all")
async def version_history(prompt_id: str, limit: int = 100, svc: VersioningService = Depends(get_versioning_service)):
    return to_dict_list(await svc.history(prompt_id, limit=limit))
