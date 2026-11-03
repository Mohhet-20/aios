"""HuggingFace Inference (text-generation-inference / serverless Inference
API) adapter. Deliberately the most different wire format of the bunch —
it's a single-prompt-string API, not a chat-messages API, and no native
tool-calling — which is exactly the case the provider abstraction needs to
prove it can absorb without leaking into the execution engine. Messages
are flattened into a role-tagged prompt string; the model just sees text.
"""
from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ai_core.providers.base import ModelProviderAdapter
from ai_core.schemas.enums import FinishReason
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import EmbeddingRequest, GenerationRequest
from ai_core.schemas.responses import EmbeddingResponse, ExecutionMetadata, GenerationResponse, StreamChunk
from ai_core.schemas.usage import TokenUsage
from ai_core.tokenizer.counter import count_message_tokens, count_tokens
from ai_core.utils.exceptions import ProviderAuthenticationError, ProviderError, ProviderRateLimitError, ProviderTimeoutError


def _flatten_prompt(messages: list[ChatMessage]) -> str:
    lines = []
    for m in messages:
        lines.append(f"<|{m.role.value}|>\n{m.text()}")
    lines.append("<|assistant|>\n")
    return "\n".join(lines)


class HuggingFaceProvider(ModelProviderAdapter):
    provider_name = "huggingface"

    def __init__(self, *, api_key: str = "", base_url: str = "https://api-inference.huggingface.co", **kwargs: Any):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        try:
            body = response.json()
            message = body.get("error", response.text) if isinstance(body, dict) else str(body)
        except Exception:  # noqa: BLE001
            message = response.text
        if response.status_code in (401, 403):
            raise ProviderAuthenticationError(message, provider=self.provider_name)
        if response.status_code == 429:
            raise ProviderRateLimitError(message, provider=self.provider_name)
        raise ProviderError(message, provider=self.provider_name, retryable=response.status_code >= 500, status_code=response.status_code)

    async def generate(self, request: GenerationRequest, *, model: str) -> GenerationResponse:
        started = time.perf_counter()
        prompt = _flatten_prompt(request.messages)
        payload: dict[str, Any] = {
            "inputs": prompt,
            "parameters": {
                "temperature": max(request.temperature, 0.01),
                "top_p": request.top_p,
                "max_new_tokens": request.max_tokens or 512,
                "return_full_text": False,
            },
        }
        try:
            resp = await self._client.post(f"{self.base_url}/models/{model}", headers=self._headers(), json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(str(exc), provider=self.provider_name) from exc
        self._raise_for_status(resp)
        data = resp.json()
        latency_ms = (time.perf_counter() - started) * 1000
        text = data[0]["generated_text"] if isinstance(data, list) else data.get("generated_text", "")
        input_tokens = count_message_tokens(request.messages, provider=self.provider_name, model=model)
        output_tokens = count_tokens(text, provider=self.provider_name, model=model)
        return GenerationResponse(
            content=text,
            finish_reason=FinishReason.STOP,
            usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens),
            execution=ExecutionMetadata(request_id=request.request_id, provider=self.provider_name, model=model, latency_ms=latency_ms),
        )

    async def stream(self, request: GenerationRequest, *, model: str) -> AsyncIterator[StreamChunk]:
        prompt = _flatten_prompt(request.messages)
        payload = {
            "inputs": prompt,
            "parameters": {"temperature": max(request.temperature, 0.01), "max_new_tokens": request.max_tokens or 512},
            "stream": True,
        }
        try:
            async with self._client.stream(
                "POST", f"{self.base_url}/models/{model}", headers=self._headers(), json=payload
            ) as resp:
                if resp.status_code >= 400:
                    await resp.aread()
                    self._raise_for_status(resp)
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    chunk = json.loads(line[len("data:"):].strip())
                    token = chunk.get("token", {})
                    is_final = bool(chunk.get("generated_text"))
                    yield StreamChunk(
                        request_id=request.request_id,
                        delta=token.get("text", ""),
                        finish_reason=FinishReason.STOP if is_final else None,
                        is_final=is_final,
                    )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(str(exc), provider=self.provider_name) from exc

    async def embed(self, request: EmbeddingRequest, *, model: str) -> EmbeddingResponse:
        texts = request.as_list()
        payload = {"inputs": texts, "options": {"wait_for_model": True}}
        try:
            resp = await self._client.post(
                f"{self.base_url}/pipeline/feature-extraction/{model}", headers=self._headers(), json=payload
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(str(exc), provider=self.provider_name) from exc
        self._raise_for_status(resp)
        embeddings = resp.json()
        return EmbeddingResponse(
            request_id=request.request_id,
            embeddings=embeddings,
            model=model,
            provider=self.provider_name,
            dimensions=len(embeddings[0]) if embeddings else 0,
            cached=[False] * len(embeddings),
        )

    async def health_check(self) -> bool:
        return bool(self.api_key)
