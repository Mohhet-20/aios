import pytest

from eval_platform.core.exceptions import ValidationError


@pytest.mark.asyncio
async def test_ingest_event_rejects_unknown_event_type(ingestion_service, workspace):
    with pytest.raises(ValidationError):
        await ingestion_service.ingest_event(workspace.id, event_type="not_real", source_platform="tool_platform", status="succeeded")


@pytest.mark.asyncio
async def test_ingest_event_rejects_unknown_status(ingestion_service, workspace):
    with pytest.raises(ValidationError):
        await ingestion_service.ingest_event(workspace.id, event_type="tool_call", source_platform="tool_platform", status="not_real")


@pytest.mark.asyncio
async def test_ingest_failed_event_requires_error_info(ingestion_service, workspace):
    with pytest.raises(ValidationError):
        await ingestion_service.ingest_event(workspace.id, event_type="tool_call", source_platform="tool_platform", status="failed")


@pytest.mark.asyncio
async def test_ingest_event_rejects_negative_retry_count(ingestion_service, workspace):
    with pytest.raises(ValidationError):
        await ingestion_service.ingest_event(workspace.id, event_type="tool_call", source_platform="tool_platform", status="succeeded", retry_count=-1)


@pytest.mark.asyncio
async def test_ingest_event_success_persists_fields(ingestion_service, workspace):
    event = await ingestion_service.ingest_event(
        workspace.id, event_type="model_usage", source_platform="prompt_platform", status="succeeded",
        source_execution_id="exec-1", latency_ms=120.5, token_usage={"input_tokens": 10, "output_tokens": 5},
        cost=0.001, resource_usage={"cpu_seconds": 0.2},
    )
    assert event.event_type == "model_usage"
    assert event.token_usage["input_tokens"] == 10
    assert event.resource_usage["cpu_seconds"] == 0.2
