import httpx
import pytest

from ai_core.providers.openai_compatible import OpenAIProvider
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest, EmbeddingRequest
from ai_core.schemas.tools import ToolDefinition
from ai_core.utils.exceptions import ProviderAuthenticationError, ProviderRateLimitError


def _make_client(handler):
    transport = httpx.MockTransport(handler)
    return httpx.AsyncClient(transport=transport, base_url="https://api.openai.com")


@pytest.mark.asyncio
async def test_generate_parses_content_and_usage():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer sk-test"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"role": "assistant", "content": "hello there"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5},
            },
        )

    provider = OpenAIProvider(api_key="sk-test", base_url="https://api.openai.com/v1", http_client=_make_client(handler))
    req = GenerationRequest(messages=[ChatMessage(role=Role.USER, content="hi")])
    resp = await provider.generate(req, model="gpt-4o-mini")
    assert resp.content == "hello there"
    assert resp.usage.input_tokens == 10
    assert resp.usage.output_tokens == 5
    assert resp.execution.provider == "openai"
    assert resp.execution.model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_generate_parses_tool_calls():
    def handler(request: httpx.Request) -> httpx.Response:
        body = request.read()
        import json

        payload = json.loads(body)
        assert payload["tools"][0]["function"]["name"] == "get_weather"
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": None,
                            "tool_calls": [
                                {"id": "call_1", "function": {"name": "get_weather", "arguments": '{"city": "SF"}'}}
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 20, "completion_tokens": 8},
            },
        )

    provider = OpenAIProvider(api_key="sk-test", http_client=_make_client(handler))
    req = GenerationRequest(
        messages=[ChatMessage(role=Role.USER, content="weather in SF?")],
        tools=[ToolDefinition(name="get_weather", description="get weather", parameters={"type": "object", "properties": {"city": {"type": "string"}}})],
    )
    resp = await provider.generate(req, model="gpt-4o")
    assert len(resp.tool_calls) == 1
    assert resp.tool_calls[0].name == "get_weather"
    assert resp.tool_calls[0].arguments == {"city": "SF"}
    assert resp.finish_reason.value == "tool_calls"


@pytest.mark.asyncio
async def test_401_raises_authentication_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid api key"}})

    provider = OpenAIProvider(api_key="bad-key", http_client=_make_client(handler))
    req = GenerationRequest(messages=[ChatMessage(role=Role.USER, content="hi")])
    with pytest.raises(ProviderAuthenticationError):
        await provider.generate(req, model="gpt-4o-mini")


@pytest.mark.asyncio
async def test_429_raises_rate_limit_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "rate limited"}}, headers={"retry-after": "2"})

    provider = OpenAIProvider(api_key="sk-test", http_client=_make_client(handler))
    req = GenerationRequest(messages=[ChatMessage(role=Role.USER, content="hi")])
    with pytest.raises(ProviderRateLimitError) as excinfo:
        await provider.generate(req, model="gpt-4o-mini")
    assert excinfo.value.retry_after_seconds == 2.0


@pytest.mark.asyncio
async def test_streaming_yields_deltas_and_final_chunk():
    sse_body = (
        'data: {"choices": [{"delta": {"content": "Hel"}, "finish_reason": null}]}\n\n'
        'data: {"choices": [{"delta": {"content": "lo"}, "finish_reason": null}]}\n\n'
        'data: {"choices": [{"delta": {}, "finish_reason": "stop"}]}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=sse_body.encode(), headers={"content-type": "text/event-stream"})

    provider = OpenAIProvider(api_key="sk-test", http_client=_make_client(handler))
    req = GenerationRequest(messages=[ChatMessage(role=Role.USER, content="hi")], stream=True)
    chunks = [c async for c in provider.stream(req, model="gpt-4o-mini")]
    full_text = "".join(c.delta for c in chunks)
    assert full_text == "Hello"
    assert chunks[-1].is_final
    assert chunks[-1].finish_reason.value == "stop"


@pytest.mark.asyncio
async def test_embed_parses_and_sorts_by_index():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "data": [{"embedding": [0.2, 0.2], "index": 1}, {"embedding": [0.1, 0.1], "index": 0}],
                "usage": {"prompt_tokens": 4},
            },
        )

    provider = OpenAIProvider(api_key="sk-test", http_client=_make_client(handler))
    req = EmbeddingRequest(input=["a", "b"])
    resp = await provider.embed(req, model="text-embedding-3-small")
    assert resp.embeddings == [[0.1, 0.1], [0.2, 0.2]]
    assert resp.dimensions == 2
