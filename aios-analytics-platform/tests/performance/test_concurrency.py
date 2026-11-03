"""Real concurrency stress tests: genuine independent DB connections
raced via `asyncio.gather`, never the rollback-isolated `repos`
fixture (which doesn't exercise real cross-connection visibility) —
the same methodology used to find and fix races in every prior AIOS
platform. This platform has three commit-spanning-lock check-then-act
sequences (see each service's module docstring):
`MetricRegistryService.register_metric` (get-or-create by metric
key), `KpiService.register_kpi` (get-or-create by KPI name within
scope), and `ReportDefinitionService.register_report` (get-or-create
by report name within report type). Each test below proves the
per-key `asyncio.Lock` actually prevents the race a naive "check then
write" sequence would produce under real concurrency."""
from __future__ import annotations

import asyncio

import pytest

from analytics_platform.database.session import session_scope
from analytics_platform.kpis.kpi_service import KpiService
from analytics_platform.repositories.registry import RepositoryRegistry
from analytics_platform.reports.report_definition_service import ReportDefinitionService
from analytics_platform.warehouse.metric_registry_service import MetricRegistryService

TENANT = "stress-tenant"


async def _register_metric_once() -> str:
    metric_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = MetricRegistryService(repos)
        definition = await service.register_metric(TENANT, key="stress.metric", name="Stress Metric", data_source="workflows")
        metric_id = definition.id
    return metric_id


@pytest.mark.asyncio
async def test_concurrent_register_metric_does_not_duplicate():
    n_callers = 15
    results = await asyncio.gather(*[_register_metric_once() for _ in range(n_callers)])

    # Every concurrent caller should have been serialized onto the SAME
    # metric definition row (same id) rather than each creating its own
    # — this is exactly the bug an unlocked "check existing, then
    # insert" sequence would produce under real concurrency.
    assert len(set(results)) == 1

    definitions = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        definitions = await repos.metric_definitions.list_for_tenant(TENANT)
    assert sum(1 for d in definitions if d.key == "stress.metric") == 1


async def _register_kpi_once() -> str:
    kpi_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = KpiService(repos)
        kpi = await service.register_kpi(TENANT, name="Stress KPI", scope="business", metric_key="stress.metric", target_value=100.0)
        kpi_id = kpi.id
    return kpi_id


@pytest.mark.asyncio
async def test_concurrent_register_kpi_does_not_duplicate():
    n_callers = 15
    results = await asyncio.gather(*[_register_kpi_once() for _ in range(n_callers)])
    assert len(set(results)) == 1

    kpis = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        kpis = await repos.kpi_definitions.list_for_tenant(TENANT, scope="business")
    assert sum(1 for k in kpis if k.name == "Stress KPI") == 1


async def _register_report_once() -> str:
    report_id = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        service = ReportDefinitionService(repos)
        definition = await service.register_report(TENANT, name="Stress Report", report_type="operational")
        report_id = definition.id
    return report_id


@pytest.mark.asyncio
async def test_concurrent_register_report_does_not_duplicate():
    n_callers = 15
    results = await asyncio.gather(*[_register_report_once() for _ in range(n_callers)])
    assert len(set(results)) == 1

    definitions = None
    async for session in session_scope():
        repos = RepositoryRegistry(session)
        definitions = await repos.report_definitions.list_for_tenant(TENANT, report_type="operational")
    assert sum(1 for d in definitions if d.name == "Stress Report") == 1
