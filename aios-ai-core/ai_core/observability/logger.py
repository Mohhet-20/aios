"""Structured logging of every AI request/response/failure/retry/fallback/
tool-call/stream-event, satisfying `ObservabilityLoggerProtocol` so
`ExecutionEngine` can be constructed with this in production and a
`NullObservabilityLogger` in tests.

Deliberately does NOT log raw message content by default — prompts and
completions routinely contain PII/secrets, so only metadata (provider,
model, token counts, latency, cost, correlation id) is logged. A future
"debug content logging" flag scoped to non-production environments would
be an explicit, reviewed opt-in, not the default here.
"""
from __future__ import annotations

from ai_core.observability.setup import get_logger
from ai_core.schemas.requests import GenerationRequest
from ai_core.schemas.responses import GenerationResponse

_logger = get_logger("ai_core.observability")


class StructlogObservabilityLogger:
    def request_started(self, request: GenerationRequest, *, candidate) -> None:
        _logger.info(
            "ai_request_started", request_id=request.request_id, provider=candidate.provider, model=candidate.name,
            stream=request.stream, has_tools=bool(request.tools),
        )

    def request_completed(self, request: GenerationRequest, response: GenerationResponse) -> None:
        _logger.info(
            "ai_request_completed",
            request_id=request.request_id,
            provider=response.execution.provider,
            model=response.execution.model,
            latency_ms=round(response.execution.latency_ms, 2),
            retries=response.execution.retries,
            fallback_used=response.execution.fallback_used,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cached_tokens=response.usage.cached_tokens,
            cost_usd=response.cost.total_cost_usd,
            finish_reason=response.finish_reason.value,
            tool_call_count=len(response.tool_calls),
        )

    def request_failed(self, request: GenerationRequest, *, candidate, error: Exception) -> None:
        _logger.error(
            "ai_request_failed", request_id=request.request_id, provider=candidate.provider, model=candidate.name,
            error_type=type(error).__name__, error=str(error),
        )

    def retry_attempted(self, request: GenerationRequest, *, candidate, attempt: int, error: Exception) -> None:
        _logger.warning(
            "ai_retry_attempted", request_id=request.request_id, provider=candidate.provider, model=candidate.name,
            attempt=attempt, error=str(error) if error else None,
        )

    def fallback_triggered(self, request: GenerationRequest, *, failed, next_candidate) -> None:
        _logger.warning(
            "ai_fallback_triggered", request_id=request.request_id, failed_model=failed.key, next_model=next_candidate.key,
        )

    def stream_chunk_emitted(self, request: GenerationRequest, *, candidate) -> None:
        _logger.debug("ai_stream_chunk_emitted", request_id=request.request_id, provider=candidate.provider, model=candidate.name)

    def tool_call_emitted(self, request: GenerationRequest, *, tool_name: str) -> None:
        _logger.info("ai_tool_call_emitted", request_id=request.request_id, tool_name=tool_name)
