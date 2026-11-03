"""The LLM Execution Engine — the single place standard, streaming, batch,
and concurrent inference actually happen. Every business service, every
gateway endpoint, everything routes through `ExecutionEngine`; nothing
calls a `ModelProviderAdapter` directly.

Responsibilities, all in one call to `generate()`/`stream()`:
  1. Validate the request.
  2. Ask the ModelRouter for an ordered fallback chain of candidate models.
  3. For each candidate, retry transient failures with exponential backoff,
     under a per-attempt timeout.
  4. If a candidate is exhausted (or its failure isn't retryable), fail
     over to the next candidate in the chain.
  5. On success: validate the response, update the registry's latency
     tracking, compute cost, record usage, and return full execution
     metadata (which provider/model actually served it, retries, whether
     fallback fired).
  6. If every candidate fails, raise AllProvidersFailedError with the full
     attempt list — callers get a real diagnostic, not a generic 500.
"""
from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator

from tenacity import AsyncRetrying, retry_if_exception, stop_after_attempt, wait_exponential

from ai_core.config.settings import AICoreSettings
from ai_core.execution.interfaces import (
    DefaultCostCalculator,
    NullObservabilityLogger,
    NullUsageTracker,
)
from ai_core.execution.validation import validate_candidate_supports_request, validate_request, validate_response
from ai_core.providers.base import ModelProviderAdapter
from ai_core.registry.model_registry import ModelRegistry
from ai_core.router.model_router import ModelRouter
from ai_core.schemas.requests import EmbeddingRequest, GenerationRequest
from ai_core.schemas.responses import EmbeddingResponse, GenerationResponse, StreamChunk
from ai_core.utils.exceptions import AllProvidersFailedError, ProviderError, RequestValidationError


class ExecutionEngine:
    def __init__(
        self,
        *,
        registry: ModelRegistry,
        router: ModelRouter,
        providers: dict[str, ModelProviderAdapter],
        settings: AICoreSettings | None = None,
        cost_calculator=None,
        usage_tracker=None,
        logger=None,
    ):
        self.registry = registry
        self.router = router
        self.providers = providers
        self.settings = settings or AICoreSettings()
        self.cost_calculator = cost_calculator or DefaultCostCalculator()
        self.usage_tracker = usage_tracker or NullUsageTracker()
        self.logger = logger or NullObservabilityLogger()

    def _get_provider(self, provider_name: str) -> ModelProviderAdapter:
        provider = self.providers.get(provider_name)
        if provider is None:
            raise ProviderError(f"No provider adapter registered for '{provider_name}'", provider=provider_name, retryable=False)
        return provider

    @staticmethod
    def _is_retryable(exc: BaseException) -> bool:
        return isinstance(exc, ProviderError) and exc.retryable

    # -- standard / batch / concurrent inference -----------------------------

    async def generate(self, request: GenerationRequest, *, cancellation_token: asyncio.Event | None = None) -> GenerationResponse:
        validate_request(request, settings=self.settings)
        self.usage_tracker.check_limits(request)
        candidates = self.router.route(request)

        attempted: list[str] = []
        total_retries = 0
        last_error: Exception | None = None
        started = time.perf_counter()

        for idx, candidate in enumerate(candidates):
            if cancellation_token is not None and cancellation_token.is_set():
                raise asyncio.CancelledError("generation cancelled by caller before candidate attempt")

            try:
                validate_candidate_supports_request(candidate, request)
            except RequestValidationError as exc:
                last_error = exc
                attempted.append(candidate.key)
                continue

            provider = self._get_provider(candidate.provider)
            self.logger.request_started(request, candidate=candidate)
            attempt_count = 0
            timeout = request.timeout_seconds or self.settings.default_request_timeout_seconds
            max_attempts = request.max_retries or self.settings.default_max_retries

            try:
                async for attempt in AsyncRetrying(
                    stop=stop_after_attempt(max_attempts),
                    wait=wait_exponential(multiplier=self.settings.retry_backoff_multiplier, max=self.settings.retry_backoff_max_seconds),
                    retry=retry_if_exception(self._is_retryable),
                    reraise=True,
                ):
                    with attempt:
                        attempt_count += 1
                        if attempt_count > 1:
                            total_retries += 1
                            self.logger.retry_attempted(request, candidate=candidate, attempt=attempt_count, error=last_error)
                        response = await asyncio.wait_for(provider.generate(request, model=candidate.name), timeout=timeout)
            except Exception as exc:  # noqa: BLE001 — deliberately broad: any failure means "try next candidate"
                last_error = exc
                attempted.append(candidate.key)
                self.logger.request_failed(request, candidate=candidate, error=exc)
                if idx + 1 < len(candidates):
                    self.logger.fallback_triggered(request, failed=candidate, next_candidate=candidates[idx + 1])
                continue

            # -- success --
            validate_response(response)
            self.registry.update_latency(candidate.provider, candidate.name, response.execution.latency_ms)
            response.execution.attempted_models = [*attempted, candidate.key]
            response.execution.retries = total_retries
            response.execution.fallback_used = idx > 0
            response.execution.latency_ms = (time.perf_counter() - started) * 1000
            response.cost = self.cost_calculator.calculate(candidate, response.usage)
            for tc in response.tool_calls:
                self.logger.tool_call_emitted(request, tool_name=tc.name)
            self.usage_tracker.record_generation(request, response)
            self.logger.request_completed(request, response)
            return response

        raise AllProvidersFailedError(
            f"All {len(candidates)} candidate(s) failed for request {request.request_id}: {attempted}", attempts=attempted
        ) from last_error

    async def generate_batch(
        self, requests: list[GenerationRequest], *, max_concurrency: int = 5
    ) -> list[GenerationResponse | Exception]:
        """Bounded-concurrency batch execution. Returns one entry per input
        request, in the same order, either a GenerationResponse or the
        Exception that request failed with — a batch never raises for a
        single bad request, callers inspect results individually."""
        semaphore = asyncio.Semaphore(max_concurrency)

        async def _run(req: GenerationRequest):
            async with semaphore:
                return await self.generate(req)

        return await asyncio.gather(*[_run(r) for r in requests], return_exceptions=True)

    async def generate_concurrent(
        self, requests: list[GenerationRequest], *, max_concurrency: int = 10
    ) -> list[GenerationResponse | Exception]:
        """Same primitive as `generate_batch` — bounded-concurrency
        `asyncio.gather` — exposed under both names because callers reach
        for "concurrent" when the goal is fan-out latency and "batch" when
        the goal is throughput over many items; the engine doesn't need two
        implementations to serve both mental models."""
        return await self.generate_batch(requests, max_concurrency=max_concurrency)

    # -- streaming ------------------------------------------------------------

    async def stream(
        self, request: GenerationRequest, *, cancellation_token: asyncio.Event | None = None
    ) -> AsyncIterator[StreamChunk]:
        """Streaming with failover *before* the first token only: once a
        candidate has started emitting chunks, content may already be
        visible to the end user, so a later mid-stream failure is raised to
        the caller rather than silently retried on a different model (which
        would produce a confusing content splice). Failover before the
        first chunk — connection refused, auth failure, timeout waiting for
        the first token — works exactly like `generate()`'s fallback chain.
        """
        validate_request(request, settings=self.settings)
        self.usage_tracker.check_limits(request)
        candidates = self.router.route(request)
        attempted: list[str] = []
        last_error: Exception | None = None
        timeout = request.timeout_seconds or self.settings.default_request_timeout_seconds

        for idx, candidate in enumerate(candidates):
            try:
                validate_candidate_supports_request(candidate, request)
            except RequestValidationError as exc:
                last_error = exc
                attempted.append(candidate.key)
                continue

            provider = self._get_provider(candidate.provider)
            self.logger.request_started(request, candidate=candidate)
            gen = provider.stream(request, model=candidate.name)
            try:
                first_chunk = await asyncio.wait_for(gen.__anext__(), timeout=timeout)
            except StopAsyncIteration:
                attempted.append(candidate.key)
                continue
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                attempted.append(candidate.key)
                self.logger.request_failed(request, candidate=candidate, error=exc)
                if idx + 1 < len(candidates):
                    self.logger.fallback_triggered(request, failed=candidate, next_candidate=candidates[idx + 1])
                continue

            # Committed to this candidate now.
            self.logger.stream_chunk_emitted(request, candidate=candidate)
            yield first_chunk
            async for chunk in gen:
                if cancellation_token is not None and cancellation_token.is_set():
                    raise asyncio.CancelledError("stream cancelled by caller")
                self.logger.stream_chunk_emitted(request, candidate=candidate)
                yield chunk
            return

        raise AllProvidersFailedError(
            f"All {len(candidates)} streaming candidate(s) failed before first token: {attempted}", attempts=attempted
        ) from last_error

    # -- embeddings -------------------------------------------------------------

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        candidates = self.router.route_embedding(request)
        attempted: list[str] = []
        last_error: Exception | None = None
        timeout = self.settings.default_request_timeout_seconds

        for candidate in candidates:
            provider = self._get_provider(candidate.provider)
            try:
                response = await asyncio.wait_for(provider.embed(request, model=candidate.name), timeout=timeout)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                attempted.append(candidate.key)
                continue
            self.usage_tracker.record_embedding(request, response)
            return response

        raise AllProvidersFailedError(
            f"All {len(candidates)} embedding candidate(s) failed: {attempted}", attempts=attempted
        ) from last_error
