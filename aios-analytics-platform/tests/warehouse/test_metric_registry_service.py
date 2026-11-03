from __future__ import annotations

import pytest

from analytics_platform.core.exceptions import MetricDefinitionNotFoundError, ValidationError
from analytics_platform.warehouse.metric_registry_service import MetricRegistryService

TENANT = "warehouse-tenant"


@pytest.mark.asyncio
async def test_register_metric_idempotent_by_key(repos):
    service = MetricRegistryService(repos)
    a = await service.register_metric(TENANT, key="api.latency", name="API Latency", data_source="api_gateway", unit="milliseconds")
    b = await service.register_metric(TENANT, key="api.latency", name="API Latency v2", data_source="api_gateway", unit="milliseconds")
    assert a.id == b.id


@pytest.mark.asyncio
async def test_register_metric_rejects_unknown_data_source(repos):
    service = MetricRegistryService(repos)
    with pytest.raises(ValidationError):
        await service.register_metric(TENANT, key="bad.metric", name="Bad", data_source="not_a_source")


@pytest.mark.asyncio
async def test_get_by_key_not_found_raises(repos):
    service = MetricRegistryService(repos)
    with pytest.raises(MetricDefinitionNotFoundError):
        await service.get_by_key(TENANT, "nonexistent.metric")


@pytest.mark.asyncio
async def test_list_for_tenant_filters_by_source(repos):
    service = MetricRegistryService(repos)
    await service.register_metric(TENANT, key="tokens.consumed", name="Tokens Consumed", data_source="models", unit="tokens")
    models_only = await service.list_for_tenant(TENANT, data_source="models")
    assert all(m.data_source == "models" for m in models_only)
    assert len(models_only) >= 1
