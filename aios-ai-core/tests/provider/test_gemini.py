import json

import httpx
import pytest

from ai_core.providers.gemini import GeminiProvider
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_generate_splits_system_instruction():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.read())
        assert payload["systemInstruction"]["parts"][0]["text"] == "Be concise."
        assert payload["contents"][0]["role"] == "user"
        return httpx.Response(
            200,
            json={
                "candidates": [{"content": {"parts": [{"text": "Ok."}]}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 6, "candidatesTokenCount": 2},
            },
        )

    provider = GeminiProvider(api_key="g-key", http_client=_client(handler))
    req = GenerationRequest(
        messages=[ChatMessage(role=Role.SYSTEM, content="Be concise."), ChatMessage(role=Role.USER, content="hi")]
    )
    resp = await provider.generate(req, model="gemini-1.5-pro")
    assert resp.content == "Ok."
    assert resp.usage.input_tokens == 6


@pytest.mark.asyncio
async def test_generate_detects_function_call():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"functionCall": {"name": "get_time", "args": {"tz": "UTC"}}}]}, "finishReason": "STOP"}
                ],
                "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 1},
            },
        )

    provider = GeminiProvider(api_key="g-key", http_client=_client(handler))
    req = GenerationRequest(messages=[ChatMessage(role=Role.USER, content="what time is it")])
    resp = await provider.generate(req, model="gemini-1.5-pro")
    assert resp.tool_calls[0].name == "get_time"
    assert resp.finish_reason.value == "tool_calls"


@pytest.mark.asyncio
async def test_streaming_concatenates_text():
    sse_body = (
        'data: {"candidates": [{"content": {"parts": [{"text": "Hel"}]}}]}\n\n'
        'data: {"candidates": [{"content": {"parts": [{"text": "lo"}]}, "finishReason": "STOP"}], "usageMetadata": {"candidatesTokenCount": 2}}\n\n'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=sse_body.encode(), headers={"content-type": "text/event-stream"})

    provider = GeminiProvider(api_key="g-key", http_client=_client(handler))
    req = GenerationRequest(messages=[ChatMessage(role=Role.USER, content="hi")], stream=True)
    chunks = [c async for c in provider.stream(req, model="gemini-1.5-pro")]
    assert "".join(c.delta for c in chunks) == "Hello"
    assert chunks[-1].is_final
