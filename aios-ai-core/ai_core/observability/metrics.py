"""Prometheus metrics for the AI Core. Counters/histograms are updated by
`PrometheusObservabilityLogger`, which satisfies the same
`ObservabilityLoggerProtocol` as the structlog logger — both can run at
once via `CompositeObservabilityLogger`."""
from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

AI_REQUESTS_TOTAL = Counter("ai_core_requests_total", "Total AI Core generation requests", ["provider", "model", "status"])
AI_REQUEST_LATENCY_MS = Histogram(
    "ai_core_request_latency_ms", "AI Core request latency in milliseconds", ["provider", "model"],
    buckets=(50, 100, 250, 500, 1000, 2000, 5000, 10000, 30000),
)
AI_TOKENS_TOTAL = Counter("ai_core_tokens_total", "Total tokens processed", ["provider", "model", "direction"])
AI_COST_USD_TOTAL = Counter("ai_core_cost_usd_total", "Total estimated cost in USD", ["provider", "model"])
AI_RETRIES_TOTAL = Counter("ai_core_retries_total", "Total retry attempts", ["provider", "model"])
AI_FALLBACKS_TOTAL = Counter("ai_core_fallbacks_total", "Total fallback events", ["failed_model", "next_model"])
AI_TOOL_CALLS_TOTAL = Counter("ai_core_tool_calls_total", "Total tool calls emitted", ["tool_name"])


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST


class PrometheusObservabilityLogger:
    def request_started(self, request, *, candidate) -> None:
        pass

    def request_completed(self, request, response) -> None:
        provider, model = response.execution.provider, response.execution.model
        AI_REQUESTS_TOTAL.labels(provider=provider, model=model, status="success").inc()
        AI_REQUEST_LATENCY_MS.labels(provider=provider, model=model).observe(response.execution.latency_ms)
        AI_TOKENS_TOTAL.labels(provider=provider, model=model, direction="input").inc(response.usage.input_tokens)
        AI_TOKENS_TOTAL.labels(provider=provider, model=model, direction="output").inc(response.usage.output_tokens)
        AI_COST_USD_TOTAL.labels(provider=provider, model=model).inc(response.cost.total_cost_usd)
        if response.execution.retries:
            AI_RETRIES_TOTAL.labels(provider=provider, model=model).inc(response.execution.retries)

    def request_failed(self, request, *, candidate, error) -> None:
        AI_REQUESTS_TOTAL.labels(provider=candidate.provider, model=candidate.name, status="failed").inc()

    def retry_attempted(self, request, *, candidate, attempt, error) -> None:
        pass

    def fallback_triggered(self, request, *, failed, next_candidate) -> None:
        AI_FALLBACKS_TOTAL.labels(failed_model=failed.key, next_model=next_candidate.key).inc()

    def stream_chunk_emitted(self, request, *, candidate) -> None:
        pass

    def tool_call_emitted(self, request, *, tool_name) -> None:
        AI_TOOL_CALLS_TOTAL.labels(tool_name=tool_name).inc()


class CompositeObservabilityLogger:
    """Fans every call out to multiple loggers — e.g. structlog for
    human/searchable logs plus Prometheus for dashboards/alerting, both
    driven by the same engine hooks."""

    def __init__(self, loggers: list):
        self._loggers = loggers

    def request_started(self, request, *, candidate) -> None:
        for logger in self._loggers:
            logger.request_started(request, candidate=candidate)

    def request_completed(self, request, response) -> None:
        for logger in self._loggers:
            logger.request_completed(request, response)

    def request_failed(self, request, *, candidate, error) -> None:
        for logger in self._loggers:
            logger.request_failed(request, candidate=candidate, error=error)

    def retry_attempted(self, request, *, candidate, attempt, error) -> None:
        for logger in self._loggers:
            logger.retry_attempted(request, candidate=candidate, attempt=attempt, error=error)

    def fallback_triggered(self, request, *, failed, next_candidate) -> None:
        for logger in self._loggers:
            logger.fallback_triggered(request, failed=failed, next_candidate=next_candidate)

    def stream_chunk_emitted(self, request, *, candidate) -> None:
        for logger in self._loggers:
            logger.stream_chunk_emitted(request, candidate=candidate)

    def tool_call_emitted(self, request, *, tool_name) -> None:
        for logger in self._loggers:
            logger.tool_call_emitted(request, tool_name=tool_name)
