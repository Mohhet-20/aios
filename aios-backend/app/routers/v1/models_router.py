from fastapi import APIRouter, Depends, status

from app.dependencies.auth_dependencies import require_permission
from app.dependencies.service_dependencies import get_model_service
from app.schemas.model import ModelCreate, ModelRead
from app.security.permissions import Permission
from app.services.model_service import ModelService

router = APIRouter(prefix="/models", tags=["Model Registry"])


@router.post("", response_model=ModelRead, status_code=status.HTTP_201_CREATED)
async def register_model(
    payload: ModelCreate,
    service: ModelService = Depends(get_model_service),
    _principal=Depends(require_permission(Permission.MODEL_MANAGE)),
):
    from app.models.model_registry import ModelRegistryEntry

    entry = ModelRegistryEntry(**payload.model_dump())
    return await service.create(entry)


@router.get("", response_model=list[ModelRead])
async def list_models(enabled_only: bool = False, service: ModelService = Depends(get_model_service)):
    return await service.list_enabled() if enabled_only else await service.list()


@router.get("/{model_id}", response_model=ModelRead)
async def get_model(model_id: str, service: ModelService = Depends(get_model_service)):
    return await service.get(model_id)
