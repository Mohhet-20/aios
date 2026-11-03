"""Evaluation identity CRUD + lifecycle, and the versioned contract
(dataset binding, metrics, scoring, target) editing/publishing that
lives underneath each evaluation."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from eval_platform.core.pagination import PaginationParams
from eval_platform.dependencies.dependencies import get_evaluation_service, get_evaluation_version_service
from eval_platform.eval_api.serialization import to_dict, to_dict_list
from eval_platform.evaluation_core.evaluation_service import EvaluationService
from eval_platform.evaluation_core.version_service import EvaluationVersionService

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


class CreateEvaluationRequest(BaseModel):
    workspace_id: str
    organization_id: str
    name: str
    owner_id: str
    category: str
    slug: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    eval_metadata: dict | None = None


class UpdateEvaluationRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    category: str | None = None
    eval_metadata: dict | None = None


class UpdateDraftRequest(BaseModel):
    dataset_id: str | None = None
    metric_keys: list[str] | None = None
    scoring_config: dict | None = None
    pass_threshold: float | None = None
    target_config: dict | None = None
    change_note: str | None = None


@router.post("", status_code=201)
async def create_evaluation(body: CreateEvaluationRequest, service: EvaluationService = Depends(get_evaluation_service)):
    evaluation = await service.create_evaluation(
        body.workspace_id, name=body.name, owner_id=body.owner_id, category=body.category,
        organization_id=body.organization_id, slug=body.slug, description=body.description,
        tags=body.tags, eval_metadata=body.eval_metadata,
    )
    return to_dict(evaluation)


@router.get("")
async def list_evaluations(
    workspace_id: str, page: int = 1, page_size: int = 50, status: str | None = None, category: str | None = None,
    service: EvaluationService = Depends(get_evaluation_service),
):
    result = await service.list_evaluations(workspace_id, PaginationParams(page=page, page_size=page_size), status=status, category=category)
    return {"items": to_dict_list(result.items), "total": result.total, "page": result.page, "page_size": result.page_size}


@router.get("/search")
async def search_evaluations(workspace_id: str, q: str, service: EvaluationService = Depends(get_evaluation_service)):
    return to_dict_list(await service.search_evaluations(workspace_id, q))


@router.get("/{evaluation_id}")
async def get_evaluation(evaluation_id: str, service: EvaluationService = Depends(get_evaluation_service)):
    return to_dict(await service.get_evaluation(evaluation_id))


@router.patch("/{evaluation_id}")
async def update_evaluation(evaluation_id: str, body: UpdateEvaluationRequest, service: EvaluationService = Depends(get_evaluation_service)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    return to_dict(await service.update_evaluation(evaluation_id, **fields))


@router.delete("/{evaluation_id}", status_code=204)
async def delete_evaluation(evaluation_id: str, service: EvaluationService = Depends(get_evaluation_service)):
    await service.delete_evaluation(evaluation_id)


@router.post("/{evaluation_id}/deprecate")
async def deprecate_evaluation(evaluation_id: str, service: EvaluationService = Depends(get_evaluation_service)):
    return to_dict(await service.deprecate(evaluation_id))


@router.post("/{evaluation_id}/archive")
async def archive_evaluation(evaluation_id: str, service: EvaluationService = Depends(get_evaluation_service)):
    return to_dict(await service.archive(evaluation_id))


# -- versions --------------------------------------------------------------------------

@router.post("/{evaluation_id}/versions/draft")
async def get_or_create_draft_version(
    evaluation_id: str, created_by: str, service: EvaluationVersionService = Depends(get_evaluation_version_service)
):
    return to_dict(await service.get_or_create_draft(evaluation_id, created_by=created_by))


@router.get("/{evaluation_id}/versions")
async def list_versions(evaluation_id: str, service: EvaluationVersionService = Depends(get_evaluation_version_service)):
    return to_dict_list(await service.list_versions(evaluation_id))


@router.get("/versions/{version_id}")
async def get_version(version_id: str, service: EvaluationVersionService = Depends(get_evaluation_version_service)):
    return to_dict(await service.get_version(version_id))


@router.patch("/versions/{version_id}")
async def update_draft_version(version_id: str, body: UpdateDraftRequest, service: EvaluationVersionService = Depends(get_evaluation_version_service)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    return to_dict(await service.update_draft(version_id, **fields))


@router.post("/versions/{version_id}/publish")
async def publish_version(version_id: str, service: EvaluationVersionService = Depends(get_evaluation_version_service)):
    return to_dict(await service.publish_version(version_id))


@router.post("/versions/{version_id}/deprecate")
async def deprecate_version(version_id: str, service: EvaluationVersionService = Depends(get_evaluation_version_service)):
    return to_dict(await service.deprecate_version(version_id))
