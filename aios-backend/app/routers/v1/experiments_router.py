from fastapi import APIRouter, Depends, Query, status

from app.dependencies.service_dependencies import get_experiment_service
from app.schemas.experiment import ExperimentCreate, ExperimentRead
from app.services.experiment_service import ExperimentService

router = APIRouter(prefix="/experiments", tags=["Experiments"])


@router.post("", response_model=ExperimentRead, status_code=status.HTTP_201_CREATED)
async def create_experiment(
    payload: ExperimentCreate, service: ExperimentService = Depends(get_experiment_service)
):
    from app.models.experiment import ExperimentModel

    experiment = ExperimentModel(
        workspace_id=payload.workspace_id,
        name=payload.name,
        hypothesis=payload.hypothesis,
        variant=payload.variant,
    )
    return await service.create(experiment)


@router.get("", response_model=list[ExperimentRead])
async def list_experiments(
    workspace_id: str | None = Query(default=None),
    service: ExperimentService = Depends(get_experiment_service),
):
    return await service.list(workspace_id=workspace_id) if workspace_id else await service.list()
