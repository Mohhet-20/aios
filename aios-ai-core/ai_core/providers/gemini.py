"""Google Gemini adapter (native `generateContent` API, not the OpenAI-
compat shim Google also offers — this talks the real wire format).
Structural differences bridged here: Gemini uses roles "user"/"model" only
(system prompts go in a separate `systemInstruction` field, like
Anthropic's `system`), tool calls are `functionCall` parts inside the
response content rather than a separate field, and tool results are sent
back as `functionResponse` parts on a "user" turn.
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
from ai_core.utils.exceptions import ProviderAuthenticationError, ProviderError, ProviderRateLimitError, ProviderTimeoutError

_FINISH_REASON_MAP = {
    "STOP": FinishReason.STOP,
    "MAX_TOKENS": FinishReason.LENGTH,
    "SAFETY": FinishReason.CONTENT_FILTER,
    "RECITATION": FinishReason.CONTENT_FILTER,
}


class GeminiProvider(ModelProviderAdapter):
    provider_name = "gemini"

    def __init__(self, *, api_key: str = "", base_url: str = "https://generativelanguage.googleapis.com", **kwargs: Any):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _split_system(self, messages: list[ChatMessage]) -> tuple[str, list[ChatMessage]]:
        system_parts = [m.text() for m in messages if m.role in (Role.SYSTEM, Role.DEVELOPER)]
        rest = [m for m in messages if m.role not in (Role.SYSTEM, Role.DEVELOPER)]
        return "\n".join(system_parts), rest

    def _serialize_parts(self, message: ChatMessage) -> list[dict[str, Any]]:
        if message.role == Role.TOOL:
            return [{"functionResponse": {"name": message.name or "unknown", "response": {"content": message.text()}}}]
        if isinstance(message.content, str):
            return [{"text": message.content}] if message.content else []
        parts = []
        for part in message.content:
            if part.type == ContentType.TEXT:
                parts.append({"text": part.text})
            elif part.type == ContentType.IMAGE_BASE64:
                parts.append({"inline_data": {"mime_type": part.mime_type, "data": part.data}})
            else:
                parts.append({"text": f"[unsupported content part: {part.type}]"})
        return parts

    def _serialize_contents(self, messages: list[ChatMessage]) -> list[dict[str, Any]]:
        out = []
        for m in messages:
            role = "model" if m.role == Role.ASSISTANT else "user"
            parts = self._serialize_parts(m)
            if m.role == Role.ASSISTANT and m.tool_calls:
                for tc in m.tool_calls:
                    parts.append({"functionCall": {"name": tc["name"], "args": tc.get("arguments", {})}})
            out.append({"role": role, "parts": parts})
        return out

    def _build_payload(self, request: GenerationRequest, *, response_format: dict | None) -> dict[str, Any]:
        system, rest = self._split_system(request.messages)
        generation_config: dict[str, Any] = {
            "temperature": request.temperature,
            "topP": request.top_p,
        }
        if request.max_tokens is not None:
            generation_config["maxOutputTokens"] = request.max_tokens
        if request.stop:
            generation_config["stopSequences"] = request.stop
        if response_format and response_format.get("type") in ("json_object", "json_schema"):
            generation_config["responseMimeType"] = "application/json"
        payload: dict[str, Any] = {"contents": self._serialize_contents(rest), "generationConfig": generation_config}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        if request.tools:
            payload["tools"] = [
                {
                    "functionDeclarations": [
                        {"name": t.name, "description": t.description, "parameters": t.parameters} for t in request.tools
                    ]
                }
            ]
        return payload

    def _raise_for_status(self, response: httpx.Response) -> None:
        if response.status_code < 400:
            return
        try:
            message = response.json().get("error", {}).get("message", response.text)
        except Exception:  # noqa: BLE001
            message = response.text
        if response.status_code in (401, 403):
            raise ProviderAuthenticationError(message, provider=self.provider_name)
        if response.status_code == 429:
            raise ProviderRateLimitError(message, provider=self.provider_name)
        raise ProviderError(message, provider=self.provider_name, retryable=response.status_code >= 500, status_code=response.status_code)

    async def generate(self, request: GenerationRequest, *, model: str) -> GenerationResponse:
        started = time.perf_counter()
        payload = self._build_payload(request, response_format=request.response_format)
        url = f"{self.base_url}/v1beta/models/{model}:generateContent?key={self.api_key}"
        try:
            resp = await self._client.post(url, json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(str(exc), provider=self.provider_name) from exc
        self._raise_for_status(resp)
        data = resp.json()
        latency_ms = (time.perf_counter() - started) * 1000
        candidate = data["candidates"][0]
        text_parts, tool_calls = [], []
        for i, part in enumerate(candidate.get("content", {}).get("parts", [])):
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                tool_calls.append(ToolCall(id=f"call_{i}", name=fc["name"], arguments=fc.get("args", {})))
        usage_raw = data.get("usageMetadata", {}) or {}
        finish = FinishReason.TOOL_CALLS if tool_calls else _FINISH_REASON_MAP.get(candidate.get("finishReason"), FinishReason.STOP)
        return GenerationResponse(
            content="".join(text_parts),
            tool_calls=tool_calls,
            finish_reason=finish,
            usage=TokenUsage(
                input_tokens=usage_raw.get("promptTokenCount", 0),
                output_tokens=usage_raw.get("candidatesTokenCount", 0),
                cached_tokens=usage_raw.get("cachedContentTokenCount", 0),
            ),
            execution=ExecutionMetadata(request_id=request.request_id, provider=self.provider_name, model=model, latency_ms=latency_ms),
        )

    async def stream(self, request: GenerationRequest, *, model: str) -> AsyncIterator[StreamChunk]:
        payload = self._build_payload(request, response_format=request.response_format)
        url = f"{self.base_url}/v1beta/models/{model}:streamGenerateContent?alt=sse&key={self.api_key}"
        try:
            async with self._client.stream("POST", url, json=payload) as resp:
                if resp.status_code >= 400:
                    await resp.aread()
                    self._raise_for_status(resp)
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    chunk = json.loads(line[len("data:"):].strip())
                    candidate = chunk["candidates"][0]
                    text = "".join(p.get("text", "") for p in candidate.get("content", {}).get("parts", []))
                    finish = candidate.get("finishReason")
                    usage_raw = chunk.get("usageMetadata", {}) or {}
                    yield StreamChunk(
                        request_id=request.request_id,
                        delta=text,
                        finish_reason=_FINISH_REASON_MAP.get(finish) if finish else None,
                        usage=TokenUsage(output_tokens=usage_raw.get("candidatesTokenCount", 0)) if finish else None,
                        is_final=finish is not None,
                    )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(str(exc), provider=self.provider_name) from exc

    async def embed(self, request: EmbeddingRequest, *, model: str) -> EmbeddingResponse:
        texts = request.as_list()
        url = f"{self.base_url}/v1beta/models/{model}:batchEmbedContents?key={self.api_key}"
        payload = {
            "requests": [
                {"model": f"models/{model}", "content": {"parts": [{"text": t}]}} for t in texts
            ]
        }
        try:
            resp = await self._client.post(url, json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(str(exc), provider=self.provider_name) from exc
        self._raise_for_status(resp)
        data = resp.json()
        embeddings = [e["values"] for e in data["embeddings"]]
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
