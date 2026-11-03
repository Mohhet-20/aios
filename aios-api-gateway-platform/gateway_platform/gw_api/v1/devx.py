"""Developer Experience: OpenAPI spec / API explorer backing, sample
requests, SDK code generation, API testing console, webhook testing."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from gateway_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_openapi_spec_service,
    get_route_service,
    get_sample_request_service,
    get_sdk_codegen_service,
    get_testing_console_service,
    get_webhook_testing_service,
)
from gateway_platform.devx.codegen_service import SdkCodeGenService
from gateway_platform.devx.openapi_service import OpenApiSpecService
from gateway_platform.devx.sample_service import SampleRequestService
from gateway_platform.devx.testing_console_service import TestingConsoleService
from gateway_platform.devx.webhook_testing_service import WebhookTestingService
from gateway_platform.gateway_core.route_service import RouteRegistrationService
from gateway_platform.gw_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/devx/openapi", tags=["developer-experience"])


@router.get("/spec.json")
async def get_openapi_spec(
    tenant_id: str = Depends(get_current_tenant_id), route_service: RouteRegistrationService = Depends(get_route_service),
    spec_service: OpenApiSpecService = Depends(get_openapi_spec_service),
):
    routes = await route_service.list_routes(tenant_id)
    return spec_service.build_spec(tenant_id, routes)


samples_router = APIRouter(prefix="/devx/samples", tags=["developer-experience"])


class GenerateSamplesRequest(BaseModel):
    json_schema: dict | None = None


@samples_router.post("")
async def generate_samples(body: GenerateSamplesRequest, service: SampleRequestService = Depends(get_sample_request_service)):
    return service.generate_samples(body.json_schema)


codegen_router = APIRouter(prefix="/devx/sdk-jobs", tags=["developer-experience"])


class CreateCodeGenJobRequest(BaseModel):
    language: str
    api_version: str


@codegen_router.post("", status_code=201)
async def create_sdk_gen_job(
    body: CreateCodeGenJobRequest, tenant_id: str = Depends(get_current_tenant_id), service: SdkCodeGenService = Depends(get_sdk_codegen_service),
):
    return to_dict(await service.create_job(tenant_id, **body.model_dump()))


class RunCodeGenJobRequest(BaseModel):
    spec: dict


@codegen_router.post("/{job_id}/run")
async def run_sdk_gen_job(
    job_id: str, body: RunCodeGenJobRequest, tenant_id: str = Depends(get_current_tenant_id), service: SdkCodeGenService = Depends(get_sdk_codegen_service),
):
    return to_dict(await service.run_job(tenant_id, job_id, spec=body.spec))


@codegen_router.get("")
async def list_sdk_gen_jobs(tenant_id: str = Depends(get_current_tenant_id), service: SdkCodeGenService = Depends(get_sdk_codegen_service)):
    return to_dict_list(await service.list_for_tenant(tenant_id))


console_router = APIRouter(prefix="/devx/test-console", tags=["developer-experience"])


class ExecuteConsoleRequest(BaseModel):
    route_id: str
    request_payload: dict


@console_router.post("/execute", status_code=201)
async def execute_test_console_request(
    body: ExecuteConsoleRequest, tenant_id: str = Depends(get_current_tenant_id), service: TestingConsoleService = Depends(get_testing_console_service),
):
    return to_dict(await service.execute(tenant_id, body.route_id, request_payload=body.request_payload))


@console_router.get("/for-route/{route_id}")
async def list_test_console_requests(
    route_id: str, tenant_id: str = Depends(get_current_tenant_id), service: TestingConsoleService = Depends(get_testing_console_service),
):
    return to_dict_list(await service.list_for_route(tenant_id, route_id))


webhook_testing_router = APIRouter(prefix="/devx/webhook-test", tags=["developer-experience"])


class SendTestWebhookRequest(BaseModel):
    target_url: str
    secret: str
    event_type: str
    payload: dict


@webhook_testing_router.post("/send")
async def send_test_webhook(body: SendTestWebhookRequest, service: WebhookTestingService = Depends(get_webhook_testing_service)):
    result = service.send_test_event(
        body.target_url, body.secret, event_type=body.event_type, payload=body.payload,
    )
    return {"success": result.success, "signature": result.signature, "error": result.error}
