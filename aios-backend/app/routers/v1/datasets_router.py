from fastapi import APIRouter, Depends, Query, status

from app.dependencies.service_dependencies import get_dataset_service
from app.schemas.dataset import DatasetCreate, DatasetRead
from app.services.dataset_service import DatasetService

router = APIRouter(prefix="/datasets", tags=["Datasets"])


@router.post("", response_model=DatasetRead, status_code=status.HTTP_201_CREATED)
async def create_dataset(payload: DatasetCreate, service: DatasetService = Depends(get_dataset_service)):
    from app.models.dataset import DatasetModel

    dataset = DatasetModel(**payload.model_dump())
    return await service.create(dataset)


@router.get("", response_model=list[DatasetRead])
async def list_datasets(
    workspace_id: str | None = Query(default=None), service: DatasetService = Depends(get_dataset_service)
):
    return await service.list(workspace_id=workspace_id) if workspace_id else await service.list()
