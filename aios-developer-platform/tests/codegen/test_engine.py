import uuid

import pytest

from developer_platform.codegen.engine import CodeGenEngine
from developer_platform.core.exceptions import CodeGenJobFailedError, CodeGenUnsupportedTargetError

pytestmark = pytest.mark.asyncio

SPEC = {
    "openapi": "3.0.3",
    "info": {"title": "Dev Platform API", "version": "v1"},
    "paths": {
        "/v1/api-keys": {"get": {"operationId": "list_api_keys", "responses": {}}},
    },
    "components": {
        "schemas": {
            "ApiKey": {"type": "object", "properties": {"id": {"type": "string"}}, "required": ["id"]},
        }
    },
}


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


async def test_create_and_run_python_job(repos, db_session):
    tenant_id = _tid()
    engine = CodeGenEngine(repos)
    job = await engine.create_job(tenant_id, target="python", source_spec_ref="self:v1")
    await db_session.commit()
    assert job.status == "queued"

    completed = await engine.run_job(tenant_id, job.id, spec=SPEC)
    await db_session.commit()
    assert completed.status == "completed"
    assert completed.finished_at is not None

    artifacts = await engine.list_artifacts(tenant_id, job.id)
    assert {a.file_path for a in artifacts} == {"client.py", "models.py"}
    for artifact in artifacts:
        assert artifact.checksum is not None
        assert artifact.size_bytes > 0


async def test_create_and_run_typescript_job(repos, db_session):
    tenant_id = _tid()
    engine = CodeGenEngine(repos)
    job = await engine.create_job(tenant_id, target="typescript", source_spec_ref="self:v1")
    await db_session.commit()

    completed = await engine.run_job(tenant_id, job.id, spec=SPEC)
    await db_session.commit()
    assert completed.status == "completed"

    artifacts = await engine.list_artifacts(tenant_id, job.id)
    assert {a.file_path for a in artifacts} == {"client.ts", "models.ts"}


async def test_unsupported_target_raises_at_create(repos, db_session):
    engine = CodeGenEngine(repos)
    with pytest.raises(CodeGenUnsupportedTargetError):
        await engine.create_job(_tid(), target="rust", source_spec_ref="self:v1")


async def test_run_job_failure_transitions_and_records_error(repos, db_session, monkeypatch):
    tenant_id = _tid()
    engine = CodeGenEngine(repos)
    job = await engine.create_job(tenant_id, target="python", source_spec_ref="self:v1")
    await db_session.commit()

    def _boom(self, spec):
        raise ValueError("generator exploded")

    import developer_platform.codegen.engine as engine_module

    monkeypatch.setattr(engine_module._GENERATORS["python"], "generate", _boom.__get__(engine_module._GENERATORS["python"]))

    with pytest.raises(CodeGenJobFailedError):
        await engine.run_job(tenant_id, job.id, spec=SPEC)
    await db_session.commit()

    jobs = await engine.list_jobs(tenant_id)
    failed = next(j for j in jobs if j.id == job.id)
    assert failed.status == "failed"
    assert "generator exploded" in failed.error
