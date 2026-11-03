from __future__ import annotations

import ast

import pytest

from gateway_platform.core.exceptions import SdkGenerationFailedError, ValidationError
from gateway_platform.devx.codegen_service import SdkCodeGenService

TENANT = "devx-codegen-tenant"

SPEC = {"paths": {"/orders": {"get": {}}, "/orders/{id}": {"delete": {}}}}


@pytest.mark.asyncio
async def test_create_job_rejects_unsupported_language(repos):
    service = SdkCodeGenService(repos)
    with pytest.raises(ValidationError):
        await service.create_job(TENANT, language="cobol", api_version="v1")


@pytest.mark.asyncio
async def test_run_job_generates_valid_python_client(repos):
    service = SdkCodeGenService(repos)
    job = await service.create_job(TENANT, language="python", api_version="v1")
    completed = await service.run_job(TENANT, job.id, spec=SPEC)
    assert completed.status == "completed"
    ast.parse(completed.artifact_ref)  # must be real, syntactically valid Python
    assert "/orders" in completed.artifact_ref


@pytest.mark.asyncio
async def test_run_job_generates_typescript_client(repos):
    service = SdkCodeGenService(repos)
    job = await service.create_job(TENANT, language="typescript", api_version="v1")
    completed = await service.run_job(TENANT, job.id, spec=SPEC)
    assert completed.status == "completed"
    assert "/orders" in completed.artifact_ref
    assert "/orders/{id}" in completed.artifact_ref


@pytest.mark.asyncio
async def test_run_job_fails_for_language_without_renderer(repos):
    service = SdkCodeGenService(repos)
    job = await service.create_job(TENANT, language="go", api_version="v1")
    with pytest.raises(SdkGenerationFailedError):
        await service.run_job(TENANT, job.id, spec=SPEC)

    jobs = await service.list_for_tenant(TENANT)
    failed = [j for j in jobs if j.id == job.id][0]
    assert failed.status == "failed"
    assert failed.error
