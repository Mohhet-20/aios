"""Metrics Registry: the catalog of every named metric a data source
can emit. `register_metric` is a get-or-create by `(tenant_id, key)`
— re-declaring a metric a source already announced returns the
existing definition (optionally refreshing its metadata) rather than
erroring, mirroring the topic/connector registration precedent used
throughout this platform family. Guarded with an in-process
`asyncio.Lock` per `(tenant_id, key)`, the same commit-spanning-lock
pattern used across every other AIOS platform's own "upsert by
identity" methods, since two concurrent callers registering the same
metric key for the first time would otherwise both observe no
existing row and both insert, producing a duplicate catalog entry."""
from __future__ import annotations

import asyncio
from collections import defaultdict

from analytics_platform.core.exceptions import MetricDefinitionNotFoundError, ValidationError
from analytics_platform.domain.enums import DataSourceType, MetricAggregationType, MetricUnit
from analytics_platform.models.warehouse import MetricDefinitionModel
from analytics_platform.repositories.registry import RepositoryRegistry


class MetricRegistryService:
    _register_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    def _assert_valid(self, *, data_source: str, unit: str, aggregation_type: str) -> None:
        if data_source not in {s.value for s in DataSourceType}:
            raise ValidationError(f"'{data_source}' is not a recognized data source")
        if unit not in {u.value for u in MetricUnit}:
            raise ValidationError(f"'{unit}' is not a recognized metric unit")
        if aggregation_type not in {a.value for a in MetricAggregationType}:
            raise ValidationError(f"'{aggregation_type}' is not a recognized aggregation type")

    async def register_metric(
        self, tenant_id: str, *, key: str, name: str, data_source: str, unit: str = "count",
        aggregation_type: str = "sum", description: str | None = None, tags: list[str] | None = None,
    ) -> MetricDefinitionModel:
        self._assert_valid(data_source=data_source, unit=unit, aggregation_type=aggregation_type)
        lock_key = f"{tenant_id}:{key}"
        async with self._register_locks[lock_key]:
            existing = await self.repos.metric_definitions.get_by_key(tenant_id, key)
            if existing is not None:
                return existing
            definition = MetricDefinitionModel(
                tenant_id=tenant_id, key=key, name=name, description=description, data_source=data_source,
                unit=unit, aggregation_type=aggregation_type, tags=tags or [],
            )
            definition = await self.repos.metric_definitions.add(definition)
            # Commit while still holding the lock — releasing it before the
            # row is durably committed would reopen the exact race the lock
            # exists to close, since a waiting caller's `get_by_key` would
            # run against a connection that can't yet see this insert.
            await self.repos.session.commit()
            return definition

    async def get_by_key(self, tenant_id: str, key: str) -> MetricDefinitionModel:
        definition = await self.repos.metric_definitions.get_by_key(tenant_id, key)
        if definition is None:
            raise MetricDefinitionNotFoundError(f"no metric definition '{key}' registered for tenant '{tenant_id}'")
        return definition

    async def list_for_tenant(self, tenant_id: str, *, data_source: str | None = None) -> list[MetricDefinitionModel]:
        return await self.repos.metric_definitions.list_for_tenant(tenant_id, data_source=data_source)
