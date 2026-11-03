"""Prometheus metrics. Three metric types cover the Observability engine's
"Metrics" requirement: a request counter (volume + error rate by
status/route), a latency histogram (p50/p95/p99 derivable in Grafana), and
an in-flight gauge (concurrency). Exposed at `GET /metrics` in Prometheus
text format via `render_metrics()`.
"""

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

REQUEST_COUNT = Counter("aios_http_requests_total", "Total HTTP requests", ["method", "path", "status_code"])
REQUEST_LATENCY = Histogram(
    "aios_http_request_duration_seconds", "HTTP request latency in seconds", ["method", "path"]
)
IN_FLIGHT_REQUESTS = Gauge("aios_http_requests_in_flight", "Requests currently being processed")

INFERENCE_REQUESTS = Counter(
    "aios_inference_requests_total", "Total inference requests", ["model_id", "status"]
)
WORKFLOW_EXECUTIONS = Counter(
    "aios_workflow_executions_total", "Total workflow executions", ["workflow_id", "status"]
)
EVENT_PUBLISHED = Counter("aios_events_published_total", "Total domain events published", ["event_name"])


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
