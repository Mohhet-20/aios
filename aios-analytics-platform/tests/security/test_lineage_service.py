from __future__ import annotations

import pytest

from analytics_platform.core.exceptions import ValidationError
from analytics_platform.security.lineage_service import DataLineageService

TENANT = "lineage-tenant"


@pytest.mark.asyncio
async def test_record_edge_rejects_bad_stage(repos):
    service = DataLineageService(repos)
    with pytest.raises(ValidationError):
        await service.record_edge(TENANT, source_ref="a", target_ref="b", stage_type="teleport")


@pytest.mark.asyncio
async def test_trace_upstream_single_hop(repos):
    service = DataLineageService(repos)
    await service.record_edge(TENANT, source_ref="raw_event", target_ref="rollup.daily", stage_type="aggregate")

    chain = await service.trace_upstream(TENANT, "rollup.daily")
    assert len(chain) == 1
    assert chain[0]["source_ref"] == "raw_event"


@pytest.mark.asyncio
async def test_trace_upstream_multi_hop(repos):
    service = DataLineageService(repos)
    await service.record_edge(TENANT, source_ref="raw_event", target_ref="metric_rollup", stage_type="aggregate")
    await service.record_edge(TENANT, source_ref="metric_rollup", target_ref="kpi_snapshot", stage_type="transform")
    await service.record_edge(TENANT, source_ref="kpi_snapshot", target_ref="dashboard_widget", stage_type="output")

    chain = await service.trace_upstream(TENANT, "dashboard_widget")
    refs = {edge["source_ref"] for edge in chain}
    assert refs == {"raw_event", "metric_rollup", "kpi_snapshot"}
    depths = {edge["source_ref"]: edge["depth"] for edge in chain}
    assert depths["kpi_snapshot"] == 1
    assert depths["raw_event"] == 3


@pytest.mark.asyncio
async def test_trace_downstream(repos):
    service = DataLineageService(repos)
    await service.record_edge(TENANT, source_ref="raw_event", target_ref="metric_rollup", stage_type="aggregate")
    await service.record_edge(TENANT, source_ref="metric_rollup", target_ref="dashboard_widget", stage_type="output")

    chain = await service.trace_downstream(TENANT, "raw_event")
    targets = {edge["target_ref"] for edge in chain}
    assert targets == {"metric_rollup", "dashboard_widget"}


@pytest.mark.asyncio
async def test_trace_upstream_no_edges_is_empty(repos):
    service = DataLineageService(repos)
    assert await service.trace_upstream(TENANT, "orphan_ref") == []


@pytest.mark.asyncio
async def test_trace_upstream_respects_max_depth(repos):
    service = DataLineageService(repos)
    await service.record_edge(TENANT, source_ref="a", target_ref="b", stage_type="transform")
    await service.record_edge(TENANT, source_ref="b", target_ref="c", stage_type="transform")
    await service.record_edge(TENANT, source_ref="c", target_ref="d", stage_type="transform")

    chain = await service.trace_upstream(TENANT, "d", max_depth=1)
    assert len(chain) == 1
    assert chain[0]["source_ref"] == "c"
