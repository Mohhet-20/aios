from __future__ import annotations

import asyncio

import pytest

from observability_platform.core.exceptions import OrphanSpanError
from observability_platform.tracing.dependency_service import TraceDependencyService
from observability_platform.tracing.span_service import SpanService
from observability_platform.tracing.trace_service import TraceService


@pytest.mark.asyncio
async def test_span_lifecycle_and_trace_finalization(repos):
    span_svc = SpanService(repos)
    trace_svc = TraceService(repos)

    root = await span_svc.start_span(
        "t1", trace_id="trace-1", span_id="root", service_name="api-gateway", operation_name="POST /chat",
    )
    await asyncio.sleep(0.001)
    child = await span_svc.start_span(
        "t1", trace_id="trace-1", span_id="child", parent_span_id="root",
        service_name="ai-core", operation_name="generate", span_kind="internal",
    )
    await span_svc.end_span("t1", child, status="ok")
    await span_svc.end_span("t1", root, status="ok")

    trace = await trace_svc.finalize_trace("t1", "trace-1")
    assert trace.span_count == 2
    assert trace.status == "ok"
    assert trace.duration_ms is not None and trace.duration_ms >= 0
    assert trace.root_service == "api-gateway"


@pytest.mark.asyncio
async def test_finalize_marks_error_status_if_any_span_errored(repos):
    span_svc = SpanService(repos)
    trace_svc = TraceService(repos)

    root = await span_svc.start_span("t1", trace_id="trace-2", span_id="root", service_name="api", operation_name="op")
    await span_svc.end_span("t1", root, status="error")

    trace = await trace_svc.finalize_trace("t1", "trace-2")
    assert trace.status == "error"


@pytest.mark.asyncio
async def test_integrity_check_detects_orphan_spans(repos):
    span_svc = SpanService(repos)
    trace_svc = TraceService(repos)

    await span_svc.start_span(
        "t1", trace_id="trace-3", span_id="child", parent_span_id="missing-parent",
        service_name="worker", operation_name="process",
    )

    orphans = await trace_svc.check_integrity("t1", "trace-3")
    assert orphans == ["child"]

    with pytest.raises(OrphanSpanError):
        await trace_svc.raise_on_orphans("t1", "trace-3")


@pytest.mark.asyncio
async def test_build_span_tree_reconstructs_hierarchy(repos):
    span_svc = SpanService(repos)
    trace_svc = TraceService(repos)

    await span_svc.start_span("t1", trace_id="trace-4", span_id="root", service_name="api", operation_name="op")
    await span_svc.start_span(
        "t1", trace_id="trace-4", span_id="child-a", parent_span_id="root", service_name="svc-a", operation_name="a"
    )
    await span_svc.start_span(
        "t1", trace_id="trace-4", span_id="child-b", parent_span_id="root", service_name="svc-b", operation_name="b"
    )
    await span_svc.start_span(
        "t1", trace_id="trace-4", span_id="grandchild", parent_span_id="child-a", service_name="svc-c", operation_name="c"
    )

    tree = await trace_svc.build_span_tree("t1", "trace-4")
    assert len(tree) == 1
    root_node = tree[0]
    assert root_node["span_id"] == "root"
    assert len(root_node["children"]) == 2
    child_a = next(c for c in root_node["children"] if c["span_id"] == "child-a")
    assert len(child_a["children"]) == 1
    assert child_a["children"][0]["span_id"] == "grandchild"


@pytest.mark.asyncio
async def test_dependency_graph_derived_from_cross_service_spans(repos):
    span_svc = SpanService(repos)

    await span_svc.start_span("t1", trace_id="trace-5", span_id="root", service_name="api", operation_name="op")
    await span_svc.start_span(
        "t1", trace_id="trace-5", span_id="s1", parent_span_id="root", service_name="ai-core", operation_name="generate"
    )
    await span_svc.start_span(
        "t1", trace_id="trace-5", span_id="s2", parent_span_id="s1", service_name="ai-core", operation_name="internal-step"
    )  # same service as parent — should NOT produce an edge
    await span_svc.start_span(
        "t1", trace_id="trace-5", span_id="s3", parent_span_id="s1", service_name="tool-platform", operation_name="call_tool"
    )

    dep_svc = TraceDependencyService(repos)
    edges = await dep_svc.service_dependencies_from_trace("t1", "trace-5")
    edge_pairs = {(e["from_service"], e["to_service"]) for e in edges}
    assert ("api", "ai-core") in edge_pairs
    assert ("ai-core", "tool-platform") in edge_pairs
    assert ("ai-core", "ai-core") not in edge_pairs
    assert len(edges) == 2
