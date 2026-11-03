import json

import httpx
import pytest

from ai_core.providers.anthropic import AnthropicProvider
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest
from ai_core.schemas.tools import ToolDefinition


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_generate_extracts_system_and_parses_text():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.read())
        assert payload["system"] == "You are a pirate."
        assert payload["max_tokens"] == 4096
        assert payload["messages"] == [{"role": "user", "content": [{"type": "text", "text": "hi"}]}]
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "Ahoy!"}],
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 12, "output_tokens": 3},
            },
        )

    provider = AnthropicProvider(api_key="sk-ant", http_client=_client(handler))
    req = GenerationRequest(
        messages=[ChatMessage(role=Role.SYSTEM, content="You are a pirate."), ChatMessage(role=Role.USER, content="hi")]
    )
    resp = await provider.generate(req, model="claude-3-5-sonnet-20241022")
    assert resp.content == "Ahoy!"
    assert resp.usage.input_tokens == 12
    assert resp.finish_reason.value == "stop"


@pytest.mark.asyncio
async def test_generate_parses_tool_use_block():
    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.read())
        assert payload["tools"][0]["name"] == "search"
        return httpx.Response(
            200,
            json={
                "content": [{"type": "tool_use", "id": "toolu_1", "name": "search", "input": {"q": "weather"}}],
                "stop_reason": "tool_use",
                "usage": {"input_tokens": 8, "output_tokens": 2},
            },
        )

    provider = AnthropicProvider(api_key="sk-ant", http_client=_client(handler))
    req = GenerationRequest(
        messages=[ChatMessage(role=Role.USER, content="search weather")],
        tools=[ToolDefinition(name="search", description="web search", parameters={"type": "object", "properties": {"q": {"type": "string"}}})],
    )
    resp = await provider.generate(req, model="claude-3-5-sonnet-20241022")
    assert resp.tool_calls[0].name == "search"
    assert resp.tool_calls[0].arguments == {"q": "weather"}
    assert resp.finish_reason.value == "tool_calls"


@pytest.mark.asyncio
async def test_streaming_text_deltas():
    sse_body = (
        'event: content_block_delta\ndata: {"delta": {"type": "text_delta", "text": "Ah"}}\n\n'
        'event: content_block_delta\ndata: {"delta": {"type": "text_delta", "text": "oy"}}\n\n'
        'event: message_delta\ndata: {"delta": {"stop_reason": "end_turn"}, "usage": {"output_tokens": 5}}\n\n'
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=sse_body.encode(), headers={"content-type": "text/event-stream"})

    provider = AnthropicProvider(api_key="sk-ant", http_client=_client(handler))
    req = GenerationRequest(messages=[ChatMessage(role=Role.USER, content="hi")], stream=True)
    chunks = [c async for c in provider.stream(req, model="claude-3-5-sonnet-20241022")]
    text = "".join(c.delta for c in chunks)
    assert text == "Ahoy"
    assert chunks[-1].is_final
    assert chunks[-1].finish_reason.value == "stop"
