"""Observability API surface: exposes correlation-ID-tagged request context
for a given trace. Full distributed tracing (span export to
Jaeger/Honeycomb via OpenTelemetry) is the natural next step here — this
endpoint is the query-side contract that implementation would fill in
without changing callers."""

from fastapi import APIRouter

from app.logging.context import get_correlation_id, get_request_id

router = APIRouter(prefix="/observability", tags=["Observability"])


@router.get("/current-context")
async def current_context():
    return {"request_id": get_request_id(), "correlation_id": get_correlation_id()}
