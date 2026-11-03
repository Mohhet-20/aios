"""Dataset identity CRUD + sharing, and the versioned item-snapshot
editing/publishing (append items, publish, deprecate) that lives
underneath each dataset."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from eval_platform.core.pagination import PaginationParams
from eval_platform.dependencies.dependencies import get_dataset_service, get_dataset_version_service
from eval_platform.datasets.dataset_service import DatasetService
from eval_platform.datasets.version_service import DatasetVersionService
from eval_platform.eval_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/datasets", tags=["datasets"])


class CreateDatasetRequest(BaseModel):
    workspace_id: str
    organization_id: str
    name: str
    owner_id: str
    dataset_type: str
    slug: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    lineage_parent_dataset_id: str | None = None
    dataset_metadata: dict | None = None


class UpdateDatasetRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    tags: list[str] | None = None
    dataset_metadata: dict | None = None


class AddItemsRequest(BaseModel):
    items: list[dict]


@router.post("", status_code=201)
async def create_dataset(body: CreateDatasetRequest, service: DatasetService = Depends(get_dataset_service)):
    dataset = await service.create_dataset(
        body.workspace_id, name=body.name, owner_id=body.owner_id, dataset_type=body.dataset_type,
        organization_id=body.organization_id, slug=body.slug, description=body.description, tags=body.tags,
        lineage_parent_dataset_id=body.lineage_parent_dataset_id, dataset_metadata=body.dataset_metadata,
    )
    return to_dict(dataset)


@router.get("")
async def list_datasets(
    workspace_id: str, page: int = 1, page_size: int = 50, status: str | None = None, dataset_type: str | None = None,
    service: DatasetService = Depends(get_dataset_service),
):
    result = await service.list_datasets(workspace_id, PaginationParams(page=page, page_size=page_size), status=status, dataset_type=dataset_type)
    return {"items": to_dict_list(result.items), "total": result.total, "page": result.page, "page_size": result.page_size}


@router.get("/shared/{workspace_id}")
async def list_shared_datasets(workspace_id: str, organization_id: str, service: DatasetService = Depends(get_dataset_service)):
    return to_dict_list(await service.list_shared_with_workspace(workspace_id, organization_id))


@router.get("/{dataset_id}")
async def get_dataset(dataset_id: str, service: DatasetService = Depends(get_dataset_service)):
    return to_dict(await service.get_dataset(dataset_id))


@router.post("/{dataset_id}/share")
async def share_dataset(dataset_id: str, target_workspace_id: str, service: DatasetService = Depends(get_dataset_service)):
    return to_dict(await service.share_with_workspace(dataset_id, target_workspace_id))


@router.patch("/{dataset_id}")
async def update_dataset(dataset_id: str, body: UpdateDatasetRequest, service: DatasetService = Depends(get_dataset_service)):
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    return to_dict(await service.update_dataset(dataset_id, **fields))


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: str, service: DatasetService = Depends(get_dataset_service)):
    await service.delete_dataset(dataset_id)


@router.post("/{dataset_id}/archive")
async def archive_dataset(dataset_id: str, service: DatasetService = Depends(get_dataset_service)):
    return to_dict(await service.archive(dataset_id))


# -- versions & items ------------------------------------------------------------------

@router.post("/{dataset_id}/versions/draft")
async def get_or_create_draft_version(dataset_id: str, created_by: str, service: DatasetVersionService = Depends(get_dataset_version_service)):
    return to_dict(await service.get_or_create_draft(dataset_id, created_by=created_by))


@router.get("/{dataset_id}/versions")
async def list_versions(dataset_id: str, service: DatasetVersionService = Depends(get_dataset_version_service)):
    return to_dict_list(await service.list_versions(dataset_id))


@router.get("/versions/{version_id}")
async def get_version(version_id: str, service: DatasetVersionService = Depends(get_dataset_version_service)):
    return to_dict(await service.get_version(version_id))


@router.post("/versions/{version_id}/items")
async def add_items(version_id: str, body: AddItemsRequest, service: DatasetVersionService = Depends(get_dataset_version_service)):
    return to_dict(await service.add_items(version_id, body.items))


@router.get("/versions/{version_id}/items")
async def list_items(version_id: str, service: DatasetVersionService = Depends(get_dataset_version_service)):
    return to_dict_list(await service.list_items(version_id))


@router.post("/versions/{version_id}/publish")
async def publish_version(version_id: str, change_note: str | None = None, service: DatasetVersionService = Depends(get_dataset_version_service)):
    return to_dict(await service.publish_version(version_id, change_note=change_note))


@router.post("/versions/{version_id}/deprecate")
async def deprecate_version(version_id: str, service: DatasetVersionService = Depends(get_dataset_version_service)):
    return to_dict(await service.deprecate_version(version_id))
