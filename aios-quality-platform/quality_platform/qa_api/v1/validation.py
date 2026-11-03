"""API & Workflow Validation: synchronous API checks and the
workflow-validation run lifecycle across the nine correctness
dimensions."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from quality_platform.dependencies.dependencies import get_api_validation_service, get_current_tenant_id, get_workflow_validation_service
from quality_platform.qa_api.serialization import to_dict, to_dict_list
from quality_platform.validation.api_validation_service import ApiValidationService
from quality_platform.validation.workflow_validation_service import WorkflowValidationRunService

router = APIRouter(prefix="/api-validation-runs", tags=["validation"])
workflow_router = APIRouter(prefix="/workflow-validation-runs", tags=["validation"])


class RunValidationRequest(BaseModel):
    validation_type: str
    target_ref: str
    errors: list[str] | None = None


@router.post("", status_code=201)
async def run_validation(
    body: RunValidationRequest, tenant_id: str = Depends(get_current_tenant_id), service: ApiValidationService = Depends(get_api_validation_service),
):
    return to_dict(await service.run_validation(tenant_id, validation_type=body.validation_type, target_ref=body.target_ref, errors=body.errors))


@router.get("")
async def list_validations(
    validation_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: ApiValidationService = Depends(get_api_validation_service),
):
    return to_dict_list(await service.list_runs(tenant_id, validation_type=validation_type))


class RequestWorkflowRunRequest(BaseModel):
    workflow_ref: str


@workflow_router.post("", status_code=201)
async def request_workflow_run(
    body: RequestWorkflowRunRequest, tenant_id: str = Depends(get_current_tenant_id), service: WorkflowValidationRunService = Depends(get_workflow_validation_service),
):
    return to_dict(await service.request_run(tenant_id, workflow_ref=body.workflow_ref))


@workflow_router.get("/{run_id}")
async def get_workflow_run(
    run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: WorkflowValidationRunService = Depends(get_workflow_validation_service),
):
    return to_dict(await service.get_or_404(tenant_id, run_id))


@workflow_router.post("/{run_id}/start")
async def start_workflow_run(
    run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: WorkflowValidationRunService = Depends(get_workflow_validation_service),
):
    return to_dict(await service.start(tenant_id, run_id))


class RecordCheckRequest(BaseModel):
    check: str
    passed: bool
    details: str = ""


@workflow_router.post("/{run_id}/checks", status_code=201)
async def record_check(
    run_id: str, body: RecordCheckRequest, tenant_id: str = Depends(get_current_tenant_id), service: WorkflowValidationRunService = Depends(get_workflow_validation_service),
):
    return to_dict(await service.record_check(tenant_id, run_id, check=body.check, passed=body.passed, details=body.details))


@workflow_router.post("/{run_id}/finish")
async def finish_workflow_run(
    run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: WorkflowValidationRunService = Depends(get_workflow_validation_service),
):
    return to_dict(await service.finish_run(tenant_id, run_id))


@workflow_router.get("")
async def list_workflow_runs(
    workflow_ref: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: WorkflowValidationRunService = Depends(get_workflow_validation_service),
):
    return to_dict_list(await service.list_runs(tenant_id, workflow_ref=workflow_ref))
