"""Test Management & Automation: suites, cases, and the run/result
lifecycle across the 15-type test pyramid."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from quality_platform.dependencies.dependencies import get_current_tenant_id, get_test_run_service, get_test_suite_service
from quality_platform.qa_api.serialization import to_dict, to_dict_list
from quality_platform.testing.test_run_service import TestRunService
from quality_platform.testing.test_suite_service import TestSuiteService

router = APIRouter(prefix="/test-suites", tags=["testing"])
runs_router = APIRouter(prefix="/test-runs", tags=["testing"])


class RegisterSuiteRequest(BaseModel):
    name: str
    test_type: str
    description: str | None = None


@router.post("", status_code=201)
async def register_suite(
    body: RegisterSuiteRequest, tenant_id: str = Depends(get_current_tenant_id), service: TestSuiteService = Depends(get_test_suite_service),
):
    return to_dict(await service.register_suite(tenant_id, **body.model_dump()))


@router.get("")
async def list_suites(
    test_type: str | None = None, tenant_id: str = Depends(get_current_tenant_id), service: TestSuiteService = Depends(get_test_suite_service),
):
    return to_dict_list(await service.list_suites(tenant_id, test_type=test_type))


@router.get("/{suite_id}")
async def get_suite(
    suite_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TestSuiteService = Depends(get_test_suite_service),
):
    return to_dict(await service.get_suite_or_404(tenant_id, suite_id))


@router.post("/{suite_id}/deactivate")
async def deactivate_suite(
    suite_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TestSuiteService = Depends(get_test_suite_service),
):
    return to_dict(await service.deactivate_suite(tenant_id, suite_id))


class AddCaseRequest(BaseModel):
    name: str
    test_type: str
    config: dict | None = None
    tags: list[str] | None = None


@router.post("/{suite_id}/cases", status_code=201)
async def add_case(
    suite_id: str, body: AddCaseRequest, tenant_id: str = Depends(get_current_tenant_id), service: TestSuiteService = Depends(get_test_suite_service),
):
    return to_dict(await service.add_case(tenant_id, suite_id, **body.model_dump()))


@router.get("/{suite_id}/cases")
async def list_cases(
    suite_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TestSuiteService = Depends(get_test_suite_service),
):
    return to_dict_list(await service.list_cases(tenant_id, suite_id))


class RequestRunRequest(BaseModel):
    suite_id: str
    triggered_by: str | None = None


@runs_router.post("", status_code=201)
async def request_run(
    body: RequestRunRequest, tenant_id: str = Depends(get_current_tenant_id), service: TestRunService = Depends(get_test_run_service),
):
    return to_dict(await service.request_run(tenant_id, body.suite_id, triggered_by=body.triggered_by))


@runs_router.get("/{run_id}")
async def get_run(
    run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TestRunService = Depends(get_test_run_service),
):
    return to_dict(await service.get_or_404(tenant_id, run_id))


@runs_router.post("/{run_id}/start")
async def start_run(
    run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TestRunService = Depends(get_test_run_service),
):
    return to_dict(await service.start(tenant_id, run_id))


class RecordResultRequest(BaseModel):
    test_case_id: str
    result: str
    duration_ms: float = 0.0
    message: str | None = None


@runs_router.post("/{run_id}/results", status_code=201)
async def record_result(
    run_id: str, body: RecordResultRequest, tenant_id: str = Depends(get_current_tenant_id), service: TestRunService = Depends(get_test_run_service),
):
    return to_dict(await service.record_result(tenant_id, run_id, body.test_case_id, result=body.result, duration_ms=body.duration_ms, message=body.message))


@runs_router.post("/{run_id}/finish")
async def finish_run(
    run_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TestRunService = Depends(get_test_run_service),
):
    return to_dict(await service.finish_run(tenant_id, run_id))


@router.get("/{suite_id}/runs")
async def list_runs(
    suite_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TestRunService = Depends(get_test_run_service),
):
    return to_dict_list(await service.list_runs(tenant_id, suite_id))
