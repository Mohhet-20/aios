import pytest

from release_platform.core.exceptions import HealthCheckFailedError, ValidationError
from release_platform.validation.health_check_service import HealthCheckService

pytestmark = pytest.mark.asyncio

TENANT = "t-validation"


async def test_record_check_rejects_unsupported_target(repos):
    svc = HealthCheckService(repos)
    with pytest.raises(ValidationError):
        await svc.record_check(TENANT, deployment_id="d1", target="carrier_pigeon_network", status="passed")


async def test_record_check_rejects_unsupported_status(repos):
    svc = HealthCheckService(repos)
    with pytest.raises(ValidationError):
        await svc.record_check(TENANT, deployment_id="d1", target="database", status="vibes_are_off")


async def test_run_all_checks_without_checker_marks_degraded(repos):
    svc = HealthCheckService(repos)
    runs = await svc.run_all_checks(TENANT, "d2")
    assert len(runs) == len(svc.settings.health_check_targets)
    assert all(r.status == "degraded" for r in runs)


async def test_run_all_checks_with_checker(repos):
    svc = HealthCheckService(repos)

    async def checker(target: str):
        return ("passed", {"target": target})

    runs = await svc.run_all_checks(TENANT, "d3", checker=checker)
    assert all(r.status == "passed" for r in runs)
    assert await svc.is_deployment_healthy(TENANT, "d3") is True


async def test_is_deployment_healthy_false_with_no_checks(repos):
    svc = HealthCheckService(repos)
    assert await svc.is_deployment_healthy(TENANT, "d-nonexistent") is False


async def test_is_deployment_healthy_false_with_one_failure(repos):
    svc = HealthCheckService(repos)

    async def checker(target: str):
        if target == "database":
            return ("failed", {})
        return ("passed", {})

    await svc.run_all_checks(TENANT, "d4", checker=checker)
    assert await svc.is_deployment_healthy(TENANT, "d4") is False


async def test_assert_healthy_raises_when_not_healthy(repos):
    svc = HealthCheckService(repos)
    with pytest.raises(HealthCheckFailedError):
        await svc.assert_healthy(TENANT, "d-nonexistent")
