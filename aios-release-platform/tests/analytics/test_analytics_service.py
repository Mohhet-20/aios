import pytest

from release_platform.analytics.analytics_service import AdoptionSnapshotService, DeploymentMetricService
from release_platform.core.exceptions import ValidationError

pytestmark = pytest.mark.asyncio

TENANT = "t-analytics"


async def test_record_metric_rejects_unknown_type(repos):
    svc = DeploymentMetricService(repos)
    with pytest.raises(ValidationError):
        await svc.record_metric(TENANT, metric_type="vibes")


async def test_deployment_success_rate(repos):
    svc = DeploymentMetricService(repos)
    await svc.record_metric(TENANT, metric_type="deployment_succeeded")
    await svc.record_metric(TENANT, metric_type="deployment_succeeded")
    await svc.record_metric(TENANT, metric_type="deployment_failed")
    rate = await svc.deployment_success_rate(TENANT)
    assert abs(rate - (2 / 3)) < 1e-9


async def test_rollback_frequency(repos):
    svc = DeploymentMetricService(repos)
    await svc.record_metric(TENANT, metric_type="deployment_succeeded")
    await svc.record_metric(TENANT, metric_type="deployment_succeeded")
    await svc.record_metric(TENANT, metric_type="rollback_triggered")
    freq = await svc.rollback_frequency(TENANT)
    assert freq == 0.5


async def test_average_deployment_duration(repos):
    svc = DeploymentMetricService(repos)
    await svc.record_metric(TENANT, metric_type="deployment_duration_seconds", value=100.0)
    await svc.record_metric(TENANT, metric_type="deployment_duration_seconds", value=200.0)
    avg = await svc.average_deployment_duration(TENANT)
    assert avg == 150.0


async def test_failed_release_count(repos):
    svc = DeploymentMetricService(repos)
    await svc.record_metric(TENANT, metric_type="release_failed")
    await svc.record_metric(TENANT, metric_type="release_failed")
    count = await svc.failed_release_count(TENANT)
    assert count == 2


async def test_adoption_snapshot_validates_range(repos):
    svc = AdoptionSnapshotService(repos)
    with pytest.raises(ValidationError):
        await svc.record_snapshot(TENANT, version="1.0.0", adoption_pct=150.0)


async def test_adoption_snapshot_latest(repos):
    svc = AdoptionSnapshotService(repos)
    assert await svc.latest_adoption(TENANT, "2.0.0") is None
    await svc.record_snapshot(TENANT, version="2.0.0", adoption_pct=10.0)
    await svc.record_snapshot(TENANT, version="2.0.0", adoption_pct=25.0)
    latest = await svc.latest_adoption(TENANT, "2.0.0")
    assert latest == 25.0
