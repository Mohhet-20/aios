import pytest

from memory_platform.document_processing.classification import DocumentClassification, classify_document


@pytest.mark.asyncio
async def test_classify_document_returns_typed_result(repos, scripted_ai_core):
    from ai_core.schemas.enums import FinishReason
    from ai_core.schemas.responses import ExecutionMetadata, GenerationResponse
    from ai_core.schemas.usage import TokenUsage
    import json as _json

    ai_core, provider = scripted_ai_core
    payload = {"categories": ["finance"], "topics": ["quarterly earnings"], "language": "en", "confidence": 0.9}
    provider.push(GenerationResponse(
        content=_json.dumps(payload), finish_reason=FinishReason.STOP, usage=TokenUsage(input_tokens=10, output_tokens=10),
        execution=ExecutionMetadata(request_id="r", provider="test", model="m1", latency_ms=1.0),
    ))
    result = await classify_document(ai_core, "Q3 earnings were up 12% year over year.")
    assert isinstance(result, DocumentClassification)
    assert result.categories == ["finance"]
    assert result.confidence == 0.9
