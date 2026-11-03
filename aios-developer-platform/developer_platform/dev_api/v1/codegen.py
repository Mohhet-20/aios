"""Code Generation: create/run jobs against a source spec, list
generated artifacts. `run_job` takes the OpenAPI-shaped `spec` dict
directly in the request body (the same shape `OpenApiSpecService.build_spec`
produces) rather than re-fetching it server-side."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from developer_platform.codegen.engine import CodeGenEngine
from developer_platform.dependencies.dependencies import get_codegen_engine, get_current_tenant_id
from developer_platform.dev_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/codegen/jobs", tags=["codegen"])


class CreateJobRequest(BaseModel):
    target: str
    source_spec_ref: str
    requested_by: str | None = None


@router.post("", status_code=201)
async def create_codegen_job(
    body: CreateJobRequest, tenant_id: str = Depends(get_current_tenant_id), engine: CodeGenEngine = Depends(get_codegen_engine),
):
    return to_dict(await engine.create_job(tenant_id, **body.model_dump()))


class RunJobRequest(BaseModel):
    spec: dict


@router.post("/{job_id}/run")
async def run_codegen_job(
    job_id: str, body: RunJobRequest, tenant_id: str = Depends(get_current_tenant_id), engine: CodeGenEngine = Depends(get_codegen_engine),
):
    return to_dict(await engine.run_job(tenant_id, job_id, spec=body.spec))


@router.get("")
async def list_codegen_jobs(tenant_id: str = Depends(get_current_tenant_id), engine: CodeGenEngine = Depends(get_codegen_engine)):
    return to_dict_list(await engine.list_jobs(tenant_id))


@router.get("/{job_id}/artifacts")
async def list_codegen_artifacts(
    job_id: str, tenant_id: str = Depends(get_current_tenant_id), engine: CodeGenEngine = Depends(get_codegen_engine),
):
    return to_dict_list(await engine.list_artifacts(tenant_id, job_id))
