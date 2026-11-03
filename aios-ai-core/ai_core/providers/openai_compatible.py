"""OpenAI wire-format adapter. This single implementation serves every
provider that speaks the OpenAI Chat Completions API shape: OpenAI itself,
Ollama, vLLM, LM Studio, and local Transformers servers (e.g. via
text-generation-webui's OpenAI-compatible mode) — each is a thin subclass
that only overrides `provider_name` and the default base_url. Azure OpenAI
reuses most of this logic too (see azure_openai.py) but needs a different
URL shape and auth header, so it overrides `_build_url`/`_build_headers`.
"""
from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx

from ai_core.providers.base import ModelProviderAdapter
from ai_core.schemas.enums import ContentType, FinishReason, Role
from ai_core.schemas.messages import ChatMessage
from ai_core.schemas.requests import EmbeddingRequest, GenerationRequest
from ai_core.schemas.responses import EmbeddingResponse, ExecutionMetadata, GenerationResponse, StreamChunk
from ai_core.schemas.tools import ToolCall
from ai_core.schemas.usage import TokenUsage
from ai_core.utils.exceptions import (
    ProviderAuthenticationError,
    ProviderError,
    ProviderRateLimitError,
    ProviderTimeoutError,
)

_FINISH_REASON_MAP = {
    "stop": FinishReason.STOP,
    "length": FinishReason.LENGTH,
    "tool_calls": FinishReason.TOOL_CALLS,
    "function_call": FinishReason.TOOL_CALLS,
    "content_filter": FinishReason.CONTENT_FILTER,
}


class OpenAICompatibleProvider(ModelProviderAdapter):
    provider_name = "openai"

    def __init__(self, *, api_key: str = "", base_url: str = "https://api.openai.com/v1", **kwargs: Any):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    # -- wire format construction -----------------------------------------

    def _build_url(self, path: str, *, model: str | None = None) -> str:
        return f"{self.base_url}{path}"

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _serialize_content(self, message: ChatMessage) -> Any:
        if isinstance(message.content, str):
            return message.content
        parts: list[dict[str, Any]] = []
        for part in message.content:
            if part.type == ContentType.TEXT:
                parts.append({"type": "text", "text": part.text})
            elif part.type == ContentType.IMAGE_URL:
                parts.append({"type": "image_url", "image_url": {"url": part.url}})
            elif part.type == ContentType.IMAGE_BASE64:
                parts.append(
                    {"type": "image_url", "image_url": {"url": f"data:{part.mime_type};base64,{part.data}"}}
                )
            else:
                # Documents/audio: OpenAI's chat API doesn't have a generic
                # slot for these today; represent as text so nothing is
                # silently dropped, and note the limitation.
                parts.append({"type": "text", "text": f"[unsupported content part: {part.type}]"})
        return parts

    def _serialize_messages(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        out = []
        for m in messages:
            entry: dict[str, Any] = {"role": m.role.value, "content": self._serialize_content(m)}
            if m.name:
                entry["name"] = m.name
            if m.role == Role.TOOL:
                entry["tool_call_id"] = m.tool_call_id
            if m.tool_calls:
                entry["tool_calls"] = m.tool_calls
            out.append(entry)
        return out

    def _build_payload(self, request: GenerationRequest, model: str, *, stream: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": self._serialize_messages(request.messages),
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": stream,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.stop:
            payload["stop"] = request.stop
        if request.tools:
            payload["tools"] = [
                {"type": "function", "function": {"name": t.name, "description": t.description, "parameters": t.parameters}}
                for t in request.tools
            ]
            payload["tool_choice"] = request.tool_choice
        if request.response_format:
            payload["response_format"] = request.response_format
        return payload

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        try:
            body = response.json()
            message = body.get("error", {}).get("message", response.text)
        except Exception:  # noqa: BLE001
            message = response.text
        if response.status_code == 401 or response.status_code == 403:
            raise ProviderAuthenticationError(message, provider=self.provider_name)
        if response.status_code == 429:
            retry_after = response.headers.get("retry-after")
            raise ProviderRateLimitError(
                message, provider=self.provider_name, retry_after_seconds=float(retry_after) if retry_after else None
            )
        retryable = response.status_code >= 500
        raise ProviderError(message, provider=self.provider_name, retryable=retryable, status_code=response.status_code)

    # -- public interface ---------------------------------------------------

    async def generate(self, request: GenerationRequest, *, model: str) -> GenerationResponse:
        started = time.perf_counter()
        payload = self._build_payload(request, model, stream=False)
        try:
            resp = await self._client.post(
                self._build_url("/chat/completions", model=model), headers=self._build_headers(), json=payload
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(str(exc), provider=self.provider_name) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(str(exc), provider=self.provider_name, retryable=True) from exc
        self._raise_for_status(resp)
        data = resp.json()
        latency_ms = (time.perf_counter() - started) * 1000
        choice = data["choices"][0]
        msg = choice.get("message", {})
        tool_calls = [
            ToolCall(id=tc["id"], name=tc["function"]["name"], arguments=self._parse_args(tc["function"].get("arguments")))
            for tc in (msg.get("tool_calls") or [])
        ]
        usage_raw = data.get("usage", {}) or {}
        usage = TokenUsage(
            input_tokens=usage_raw.get("prompt_tokens", 0),
            output_tokens=usage_raw.get("completion_tokens", 0),
            cached_tokens=(usage_raw.get("prompt_tokens_details") or {}).get("cached_tokens", 0),
        )
        return GenerationResponse(
            content=msg.get("content") or "",
            tool_calls=tool_calls,
            finish_reason=_FINISH_REASON_MAP.get(choice.get("finish_reason"), FinishReason.STOP),
            usage=usage,
            execution=ExecutionMetadata(
                request_id=request.request_id, provider=self.provider_name, model=model, latency_ms=latency_ms
            ),
        )

    @staticmethod
    def _parse_args(raw: str | None) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"_raw": raw}

    async def stream(self, request: GenerationRequest, *, model: str) -> AsyncIterator[StreamChunk]:
        payload = self._build_payload(request, model, stream=True)
        try:
            async with self._client.stream(
                "POST", self._build_url("/chat/completions", model=model), headers=self._build_headers(), json=payload
            ) as resp:
                if resp.status_code >= 400:
                    await resp.aread()
                    self._raise_for_status(resp)
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[len("data:"):].strip()
                    if data_str == "[DONE]":
                        break
                    chunk = json.loads(data_str)
                    choice = chunk["choices"][0]
                    delta = choice.get("delta", {})
                    finish = choice.get("finish_reason")
                    yield StreamChunk(
                        request_id=request.request_id,
                        delta=delta.get("content") or "",
                        tool_call_delta={"tool_calls": delta["tool_calls"]} if delta.get("tool_calls") else None,
                        finish_reason=_FINISH_REASON_MAP.get(finish) if finish else None,
                        is_final=finish is not None,
                    )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(str(exc), provider=self.provider_name) from exc

    async def embed(self, request: EmbeddingRequest, *, model: str) -> EmbeddingResponse:
        payload = {"model": model, "input": request.as_list()}
        try:
            resp = await self._client.post(self._build_url("/embeddings", model=model), headers=self._build_headers(), json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(str(exc), provider=self.provider_name) from exc
        self._raise_for_status(resp)
        data = resp.json()
        embeddings = [item["embedding"] for item in sorted(data["data"], key=lambda d: d["index"])]
        usage_raw = data.get("usage", {}) or {}
        return EmbeddingResponse(
            request_id=request.request_id,
            embeddings=embeddings,
            model=model,
            provider=self.provider_name,
            dimensions=len(embeddings[0]) if embeddings else 0,
            usage=TokenUsage(input_tokens=usage_raw.get("prompt_tokens", 0)),
            cached=[False] * len(embeddings),
        )

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(self._build_url("/models"), headers=self._build_headers())  # no model context for health checks
            return resp.status_code < 500
        except httpx.HTTPError:
            return False


class OpenAIProvider(OpenAICompatibleProvider):
    provider_name = "openai"


class OllamaProvider(OpenAICompatibleProvider):
    provider_name = "ollama"

    def __init__(self, *, base_url: str = "http://localhost:11434/v1", **kwargs: Any):
        super().__init__(api_key="", base_url=base_url, **kwargs)


class VLLMProvider(OpenAICompatibleProvider):
    provider_name = "vllm"

    def __init__(self, *, base_url: str = "http://localhost:8000/v1", api_key: str = "", **kwargs: Any):
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)


class LMStudioProvider(OpenAICompatibleProvider):
    provider_name = "lmstudio"

    def __init__(self, *, base_url: str = "http://localhost:1234/v1", **kwargs: Any):
        super().__init__(api_key="", base_url=base_url, **kwargs)


class LocalTransformersProvider(OpenAICompatibleProvider):
    """Targets any local server exposing the OpenAI-compatible surface on
    top of a `transformers`-loaded model (e.g. text-generation-webui,
    a custom FastAPI wrapper). Same wire format, different default port."""

    provider_name = "local_transformers"

    def __init__(self, *, base_url: str = "http://localhost:9000/v1", **kwargs: Any):
        super().__init__(api_key="", base_url=base_url, **kwargs)
