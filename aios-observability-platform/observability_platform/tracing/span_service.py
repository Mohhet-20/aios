"""Span ingestion. Spans from a real distributed system routinely
arrive out of order (a child service's span can be flushed and ingested
before its parent's), so `start_span` never validates that
`parent_span_id` already exists — that would reject perfectly valid
traces just because of network/flush timing. Integrity checking (does
every non-null parent_span_id actually resolve to a span in the same
trace) is a separate, explicit, post-hoc operation on `TraceService`,
run once a trace is considered complete."""
from __future__ import annotations

from datetime import datetime

from observability_platform.config.settings import Settings, get_settings
from observability_platform.core.exceptions import ValidationError
from observability_platform.database.base import utcnow
from observability_platform.domain.entities import _aware
from observability_platform.domain.enums import SpanKind, SpanStatus
from observability_platform.models.tracing import SpanModel
from observability_platform.repositories.registry import RepositoryRegistry


class SpanService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def start_span(
        self,
        tenant_id: str,
        *,
        trace_id: str,
        span_id: str,
        service_name: str,
        operation_name: str,
        parent_span_id: str | None = None,
        span_kind: str = SpanKind.INTERNAL.value,
        attributes: dict | None = None,
        start_time: datetime | None = None,
    ) -> SpanModel:
        if span_kind not in {k.value for k in SpanKind}:
            raise ValidationError(f"Unknown span kind '{span_kind}'")
        span = SpanModel(
            tenant_id=tenant_id, trace_id=trace_id, span_id=span_id, parent_span_id=parent_span_id,
            service_name=service_name, operation_name=operation_name, span_kind=span_kind,
            status=SpanStatus.UNSET.value, attributes=attributes or {}, start_time=start_time or utcnow(),
        )
        return await self.repos.spans.add(span)

    async def end_span(
        self,
        tenant_id: str,
        span: SpanModel,
        *,
        status: str = SpanStatus.OK.value,
        end_time: datetime | None = None,
        attributes_update: dict | None = None,
    ) -> SpanModel:
        if status not in {s.value for s in SpanStatus}:
            raise ValidationError(f"Unknown span status '{status}'")
        span.end_time = end_time or utcnow()
        span.status = status
        # `span.start_time` may have round-tripped through SQLite (which
        # drops tzinfo) if this span object was freshly fetched rather
        # than the one `start_span` just returned in the same session —
        # the REST layer's end-span endpoint does exactly that lookup.
        span.duration_ms = (span.end_time - _aware(span.start_time)).total_seconds() * 1000
        if attributes_update:
            span.attributes = {**span.attributes, **attributes_update}
        return await self.repos.spans.update(span)

    async def list_for_trace(self, tenant_id: str, trace_id: str) -> list[SpanModel]:
        return await self.repos.spans.list_for_trace(tenant_id, trace_id)
