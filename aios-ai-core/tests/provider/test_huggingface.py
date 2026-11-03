import httpx
import pytest

from ai_core.providers.huggingface import HuggingFaceProvider
from ai_core.schemas.enums import Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import GenerationRequest, EmbeddingRequest


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.mark.asyncio
async def test_generate_flattens_prompt_and_parses_response():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        captured["payload"] = json.loads(request.read())
        return httpx.Response(200, json=[{"generated_text": "The answer is 4."}])

    provider = HuggingFaceProvider(api_key="hf-key", http_client=_client(handler))
    req = GenerationRequest(messages=[ChatMessage(role=Role.USER, content="what is 2+2?")])
    resp = await provider.generate(req, model="meta-llama/Llama-3-8b")
    assert resp.content == "The answer is 4."
    assert "<|user|>" in captured["payload"]["inputs"]
    assert resp.usage.input_tokens > 0


@pytest.mark.asyncio
async def test_embed_returns_raw_vectors():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=[[0.1, 0.2], [0.3, 0.4]])

    provider = HuggingFaceProvider(api_key="hf-key", http_client=_client(handler))
    req = EmbeddingRequest(input=["a", "b"])
    resp = await provider.embed(req, model="sentence-transformers/all-MiniLM-L6-v2")
    assert resp.embeddings == [[0.1, 0.2], [0.3, 0.4]]
    assert resp.dimensions == 2
