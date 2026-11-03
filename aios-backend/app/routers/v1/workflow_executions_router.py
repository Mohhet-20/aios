"""Standalone execution lookup (`/executions/{id}`) alongside the nested
`/workflows/{id}/executions` list — the same resource addressed both by
its own ID (for status polling) and via its parent (for history browsing)."""

from fastapi import APIRouter, Depends

from app.dependencies.service_dependencies import get_workflow_service
from app.schemas.workflow import WorkflowExecutionRead
from app.services.workflow_service import WorkflowService

router = APIRouter(prefix="/executions", tags=["Workflow Executions"])


@router.get("/{execution_id}", response_model=WorkflowExecutionRead)
async def get_execution(execution_id: str, service: WorkflowService = Depends(get_workflow_service)):
    return await service.get_execution(execution_id)
