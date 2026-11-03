import pytest

from docs_platform.automation.generation_job_service import GenerationJobService
from docs_platform.core.exceptions import InvalidTransitionError, UnsupportedGenerationJobTypeError

pytestmark = pytest.mark.asyncio


async def test_request_job_rejects_unsupported_type(repos):
    svc = GenerationJobService(repos)
    with pytest.raises(UnsupportedGenerationJobTypeError):
        await svc.request_job("t1", job_type="not-a-type", target_ref="svc:1")


async def test_run_job_with_no_generator_completes_honestly(repos):
    svc = GenerationJobService(repos)
    job = await svc.request_job("t1", job_type="api_docs", target_ref="svc:1")
    finished = await svc.run_job("t1", job.id)
    assert finished.status == "completed"
    assert finished.result["generated"] is False


async def test_run_job_with_generator_completes_with_result(repos):
    svc = GenerationJobService(repos)
    job = await svc.request_job("t1", job_type="changelog", target_ref="svc:2")

    async def _generator(j):
        return {"entries": ["Added X", "Fixed Y"]}

    finished = await svc.run_job("t1", job.id, generator=_generator)
    assert finished.status == "completed"
    assert finished.result["entries"] == ["Added X", "Fixed Y"]


async def test_run_job_generator_failure_fails_job(repos):
    svc = GenerationJobService(repos)
    job = await svc.request_job("t1", job_type="sdk_docs", target_ref="svc:3")

    async def _bad_generator(j):
        raise RuntimeError("boom")

    finished = await svc.run_job("t1", job.id, generator=_bad_generator)
    assert finished.status == "failed"
    assert "boom" in finished.error


async def test_cannot_complete_without_start(repos):
    svc = GenerationJobService(repos)
    job = await svc.request_job("t1", job_type="dependency_report", target_ref="svc:4")
    with pytest.raises(InvalidTransitionError):
        await svc.complete("t1", job.id, result={})
