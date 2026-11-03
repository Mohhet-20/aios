from fastapi import APIRouter, Depends, Query, status

from app.dependencies.auth_dependencies import require_permission
from app.dependencies.service_dependencies import get_workflow_service
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowExecuteRequest,
    WorkflowExecutionRead,
    WorkflowRead,
)
from app.security.permissions import Permission
from app.security.principal import Principal
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/workflows", tags=["Workflows"])


@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    payload: WorkflowCreate,
    service: WorkflowService = Depends(get_workflow_service),
    _principal=Depends(require_permission(Permission.WORKFLOW_WRITE)),
):
    from app.models.workflow import WorkflowModel

    workflow = WorkflowModel(
        workspace_id=payload.workspace_id,
        name=payload.name,
        description=payload.description,
        definition=payload.definition,
    )
    return await service.workflows.add(workflow)


@router.get("", response_model=list[WorkflowRead])
async def list_workflows(
    workspace_id: str | None = Query(default=None), service: WorkflowService = Depends(get_workflow_service)
):
    return (
        await service.workflows.list(workspace_id=workspace_id)
        if workspace_id
        else await service.workflows.list()
    )


@router.get("/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(workflow_id: str, service: WorkflowService = Depends(get_workflow_service)):
    return await service.workflows.get_or_404(workflow_id)


@router.post(
    "/{workflow_id}/execute", response_model=WorkflowExecutionRead, status_code=status.HTTP_202_ACCEPTED
)
async def execute_workflow(
    workflow_id: str,
    payload: WorkflowExecuteRequest,
    service: WorkflowService = Depends(get_workflow_service),
    principal: Principal = Depends(require_permission(Permission.WORKFLOW_EXECUTE)),
):
    return await service.execute(workflow_id, payload.input_payload, principal.id)


@router.get("/{workflow_id}/executions", response_model=list[WorkflowExecutionRead])
async def list_executions(workflow_id: str, service: WorkflowService = Depends(get_workflow_service)):
    return await service.executions.list_for_workflow(workflow_id)
