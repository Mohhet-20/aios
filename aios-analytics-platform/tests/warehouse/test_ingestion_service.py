from __future__ import annotations

import pytest

from analytics_platform.config.settings import Settings
from analytics_platform.core.exceptions import EventIngestionError, MetricDefinitionNotFoundError, UnsupportedDataSourceError
from analytics_platform.warehouse.ingestion_service import EventIngestionService
from analytics_platform.warehouse.metric_registry_service import MetricRegistryService

TENANT = "ingestion-tenant"


@pytest.mark.asyncio
async def test_ingest_event_requires_registered_metric(repos):
    ingestion = EventIngestionService(repos)
    with pytest.raises(MetricDefinitionNotFoundError):
        await ingestion.ingest_event(TENANT, metric_key="unregistered.metric", data_source="agents", value=1.0)


@pytest.mark.asyncio
async def test_ingest_event_rejects_unsupported_source(repos):
    registry = MetricRegistryService(repos)
    await registry.register_metric(TENANT, key="agent.tasks", name="Agent Tasks", data_source="agents")
    ingestion = EventIngestionService(repos, registry=registry)
    with pytest.raises(UnsupportedDataSourceError):
        await ingestion.ingest_event(TENANT, metric_key="agent.tasks", data_source="carrier_pigeon", value=1.0)


@pytest.mark.asyncio
async def test_ingest_and_list_events(repos):
    registry = MetricRegistryService(repos)
    await registry.register_metric(TENANT, key="workflow.completed", name="Workflows Completed", data_source="workflows")
    ingestion = EventIngestionService(repos, registry=registry)

    await ingestion.ingest_event(TENANT, metric_key="workflow.completed", data_source="workflows", value=1.0, dimensions={"workspace_id": "w1"})
    await ingestion.ingest_event(TENANT, metric_key="workflow.completed", data_source="workflows", value=1.0, dimensions={"workspace_id": "w2"})

    events = await ingestion.list_for_metric(TENANT, "workflow.completed")
    assert len(events) == 2


@pytest.mark.asyncio
async def test_ingest_batch_respects_max_size(repos):
    registry = MetricRegistryService(repos)
    await registry.register_metric(TENANT, key="prompt.executed", name="Prompts Executed", data_source="prompts")
    settings = Settings(warehouse_batch_ingest_max_size=2)
    ingestion = EventIngestionService(repos, settings=settings, registry=registry)

    oversized_batch = [
        {"metric_key": "prompt.executed", "data_source": "prompts", "value": 1.0} for _ in range(3)
    ]
    with pytest.raises(EventIngestionError):
        await ingestion.ingest_batch(TENANT, oversized_batch)


@pytest.mark.asyncio
async def test_ingest_batch_success(repos):
    registry = MetricRegistryService(repos)
    await registry.register_metric(TENANT, key="tool.invoked", name="Tool Invocations", data_source="tools")
    ingestion = EventIngestionService(repos, registry=registry)

    batch = [{"metric_key": "tool.invoked", "data_source": "tools", "value": 1.0} for _ in range(3)]
    recorded = await ingestion.ingest_batch(TENANT, batch)
    assert len(recorded) == 3


@pytest.mark.asyncio
async def test_sweep_retention(repos):
    registry = MetricRegistryService(repos)
    await registry.register_metric(TENANT, key="deploy.count", name="Deployments", data_source="deployments")
    ingestion = EventIngestionService(repos, registry=registry)
    await ingestion.ingest_event(TENANT, metric_key="deploy.count", data_source="deployments", value=1.0)

    deleted = await ingestion.sweep_retention(TENANT)
    assert deleted == 0  # nothing old enough to sweep yet
