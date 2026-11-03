import structlog

from ai_core.observability.context import get_correlation_id, set_correlation_id
from ai_core.observability.logger import StructlogObservabilityLogger
from ai_core.registry.model_metadata import ModelMetadata
from ai_core.schemas.enums import FinishReason, Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest
from ai_core.schemas.responses import ExecutionMetadata, GenerationResponse
from ai_core.schemas.usage import CostBreakdown, TokenUsage


def _req() -> GenerationRequest:
    return GenerationRequest(messages=[ChatMessage(role=Role.USER, content="hi")])


def _candidate() -> ModelMetadata:
    return ModelMetadata(provider="openai", name="gpt-4o")


def test_correlation_id_roundtrip():
    cid = set_correlation_id()
    assert get_correlation_id() == cid
    set_correlation_id("fixed-id")
    assert get_correlation_id() == "fixed-id"


def test_request_completed_logs_metadata_not_raw_content():
    logger = StructlogObservabilityLogger()
    req = _req()
    resp = GenerationResponse(
        content="the secret answer is 42",
        finish_reason=FinishReason.STOP,
        usage=TokenUsage(input_tokens=10, output_tokens=5),
        cost=CostBreakdown(total_cost_usd=0.01),
        execution=ExecutionMetadata(request_id=req.request_id, provider="openai", model="gpt-4o", latency_ms=123.4),
    )
    with structlog.testing.capture_logs() as captured:
        logger.request_completed(req, resp)

    assert len(captured) == 1
    entry = captured[0]
    assert entry["event"] == "ai_request_completed"
    assert entry["provider"] == "openai"
    assert entry["cost_usd"] == 0.01
    assert "the secret answer" not in str(entry)


def test_request_failed_logs_error_type():
    logger = StructlogObservabilityLogger()
    with structlog.testing.capture_logs() as captured:
        logger.request_failed(_req(), candidate=_candidate(), error=ValueError("boom"))
    assert captured[0]["event"] == "ai_request_failed"
    assert captured[0]["error_type"] == "ValueError"


def test_fallback_triggered_logs_both_model_keys():
    logger = StructlogObservabilityLogger()
    failed = ModelMetadata(provider="openai", name="gpt-4o")
    next_candidate = ModelMetadata(provider="anthropic", name="claude-3-5-sonnet-20241022")
    with structlog.testing.capture_logs() as captured:
        logger.fallback_triggered(_req(), failed=failed, next_candidate=next_candidate)
    assert captured[0]["failed_model"] == "openai:gpt-4o"
    assert captured[0]["next_model"] == "anthropic:claude-3-5-sonnet-20241022"
