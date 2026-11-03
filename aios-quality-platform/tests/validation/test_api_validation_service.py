import pytest

from quality_platform.core.exceptions import UnsupportedApiValidationTypeError
from quality_platform.validation.api_validation_service import ApiValidationService

pytestmark = pytest.mark.asyncio


async def test_run_validation_rejects_unsupported_type(repos):
    svc = ApiValidationService(repos)
    with pytest.raises(UnsupportedApiValidationTypeError):
        await svc.run_validation("t1", validation_type="not-a-type", target_ref="api:1")


async def test_run_validation_passes_with_no_errors(repos):
    svc = ApiValidationService(repos)
    run = await svc.run_validation("t1", validation_type="schema", target_ref="api:1")
    assert run.outcome == "passed"
    assert run.details["errors"] == []


async def test_run_validation_fails_with_errors(repos):
    svc = ApiValidationService(repos)
    run = await svc.run_validation("t1", validation_type="contract", target_ref="api:2", errors=["missing field 'id'"])
    assert run.outcome == "failed"
    assert run.details["errors"] == ["missing field 'id'"]


async def test_list_runs_filters_by_type(repos):
    svc = ApiValidationService(repos)
    await svc.run_validation("t1", validation_type="backward_compatibility", target_ref="api:3")
    await svc.run_validation("t1", validation_type="sdk_compatibility", target_ref="api:4")
    backward_only = await svc.list_runs("t1", validation_type="backward_compatibility")
    assert len(backward_only) == 1
