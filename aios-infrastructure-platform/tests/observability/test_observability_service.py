"""Tests for Infra Observability: metric recording/lookup, retention
pruning, deployment success-rate aggregation, and cluster health
checks."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from infra_platform.config.settings import Settings
from infra_platform.observability.observability_service import ClusterHealthService, InfraMetricService

TENANT = "tenant-observability"


@pytest.mark.asyncio
async def test_record_and_query_metrics(repos):
    service = InfraMetricService(repos)
    await service.record_metric(TENANT, metric_name="cpu_utilization", value=45.0, resource_type="node_pool", resource_id="pool-1")
    await service.record_metric(TENANT, metric_name="cpu_utilization", value=60.0, resource_type="node_pool", resource_id="pool-1")

    recent = await service.list_recent(TENANT, metric_name="cpu_utilization")
    assert len(recent) == 2

    latest = await service.latest_for_metric(TENANT, "cpu_utilization", resource_id="pool-1")
    assert latest.value == 60.0


@pytest.mark.asyncio
async def test_prune_old_metrics(repos):
    service = InfraMetricService(repos, settings=Settings(metric_retention_days=30))
    old = await service.record_metric(TENANT, metric_name="latency_ms", value=100.0)
    old.recorded_at = datetime.now(timezone.utc) - timedelta(days=45)
    await repos.infra_metrics.update(old)

    await service.record_metric(TENANT, metric_name="latency_ms", value=90.0)

    pruned = await service.prune_old_metrics(TENANT)
    assert pruned == 1
    remaining = await service.list_recent(TENANT, metric_name="latency_ms")
    assert len(remaining) == 1
    assert remaining[0].value == 90.0


@pytest.mark.asyncio
async def test_deployment_success_rate(repos):
    from infra_platform.deployment.deployment_service import DeploymentService

    deploy_service = DeploymentService(repos)
    obs_service = InfraMetricService(repos, settings=Settings(deployment_success_rate_alert_threshold=0.9))

    for i in range(3):
        d = await deploy_service.create_deployment(TENANT, name=f"svc-{i}", target_version="1.0.0")
        await deploy_service.start(TENANT, d.id)
        await deploy_service.succeed(TENANT, d.id)

    failing = await deploy_service.create_deployment(TENANT, name="svc-fail", target_version="1.0.0")
    await deploy_service.start(TENANT, failing.id)
    with pytest.raises(Exception):
        await deploy_service.fail(TENANT, failing.id)

    result = await obs_service.deployment_success_rate(TENANT)
    assert result["rate"] == pytest.approx(0.75)
    assert result["below_threshold"] is True


@pytest.mark.asyncio
async def test_cluster_health_checks(repos):
    service = ClusterHealthService(repos)
    await service.record_health_check(TENANT, "cluster-1", status="healthy", details={"nodes_ready": 5})
    await service.record_health_check(TENANT, "cluster-1", status="degraded", details={"nodes_ready": 3})

    latest = await service.latest_for_cluster(TENANT, "cluster-1")
    assert latest.status == "degraded"

    history = await service.list_for_cluster(TENANT, "cluster-1")
    assert len(history) == 2
