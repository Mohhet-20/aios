from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth_dependencies import require_permission
from app.dependencies.service_dependencies import get_evaluation_service
from app.schemas.evaluation import EvaluationRunCreate, EvaluationRunRead
from app.security.permissions import Permission
from app.services.evaluation_service import EvaluationService

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])


@router.post("", response_model=EvaluationRunRead, status_code=status.HTTP_202_ACCEPTED)
async def run_evaluation_suite(
    payload: EvaluationRunCreate,
    service: EvaluationService = Depends(get_evaluation_service),
    _principal=Depends(require_permission(Permission.EVALUATION_WRITE)),
):
    return await service.run_suite(
        payload.workspace_id, payload.suite_name, payload.target_type, payload.target_id, payload.dataset_id
    )


@router.get("", response_model=list[EvaluationRunRead])
async def list_evaluations(
    workspace_id: str | None = Query(default=None),
    service: EvaluationService = Depends(get_evaluation_service),
):
    return (
        await service.repository.list(workspace_id=workspace_id)
        if workspace_id
        else await service.repository.list()
    )


@router.get("/{run_id}", response_model=EvaluationRunRead)
async def get_evaluation(run_id: str, service: EvaluationService = Depends(get_evaluation_service)):
    return await service.repository.get_or_404(run_id)


@router.post("/{run_id}/complete", response_model=EvaluationRunRead)
async def complete_evaluation(
    run_id: str, passed: int, failed: int, service: EvaluationService = Depends(get_evaluation_service)
):
    """Called by the evaluation background job once grading finishes; also
    exposed directly so this can be exercised/tested without waiting on the
    worker pool."""
    return await service.complete_run(run_id, passed, failed)
