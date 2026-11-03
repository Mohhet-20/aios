"""Anthropic Messages API adapter. Anthropic's wire format differs from
OpenAI's in three structural ways this adapter bridges: (1) system prompts
are a top-level `system` field, not a message with role=system, (2)
`max_tokens` is required on every request, and (3) tool calls/results are
content blocks (`tool_use`/`tool_result`) inside a message's `content`
list rather than separate `tool_calls`/`tool_call_id` fields.
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
from ai_core.schemas.requests import GenerationRequest
from ai_core.schemas.responses import ExecutionMetadata, GenerationResponse, StreamChunk
from ai_core.schemas.tools import ToolCall
from ai_core.schemas.usage import TokenUsage
from ai_core.utils.exceptions import ProviderAuthenticationError, ProviderError, ProviderRateLimitError, ProviderTimeoutError

_STOP_REASON_MAP = {
    "end_turn": FinishReason.STOP,
    "stop_sequence": FinishReason.STOP,
    "max_tokens": FinishReason.LENGTH,
    "tool_use": FinishReason.TOOL_CALLS,
}

_DEFAULT_MAX_TOKENS = 4096


class AnthropicProvider(ModelProviderAdapter):
    provider_name = "anthropic"

    def __init__(self, *, api_key: str = "", base_url: str = "https://api.anthropic.com", **kwargs: Any):
        super().__init__(**kwargs)
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }

    def _split_system(self, messages: list[ChatMessage]) -> tuple[str, list[ChatMessage]]:
        system_parts = [m.text() for m in messages if m.role in (Role.SYSTEM, Role.DEVELOPER)]
        rest = [m for m in messages if m.role not in (Role.SYSTEM, Role.DEVELOPER)]
        return "\n".join(system_parts), rest

    def _serialize_content(self, message: ChatMessage) -> list[dict[str, Any]]:
        if message.role == Role.TOOL:
            return [
                {
                    "type": "tool_result",
                    "tool_use_id": message.tool_call_id,
                    "content": message.text() or str(message.content),
                }
            ]
        if isinstance(message.content, str):
            blocks: list[dict[str, Any]] = [{"type": "text", "text": message.content}] if message.content else []
        else:
            blocks = []
            for part in message.content:
                if part.type == ContentType.TEXT:
                    blocks.append({"type": "text", "text": part.text})
                elif part.type == ContentType.IMAGE_BASE64:
                    blocks.append(
                        {"type": "image", "source": {"type": "base64", "media_type": part.mime_type, "data": part.data}}
                    )
                elif part.type == ContentType.IMAGE_URL:
                    blocks.append({"type": "image", "source": {"type": "url", "url": part.url}})
                else:
                    blocks.append({"type": "text", "text": f"[unsupported content part: {part.type}]"})
        if message.role == Role.ASSISTANT and message.tool_calls:
            for tc in message.tool_calls:
                blocks.append({"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc.get("arguments", {})})
        return blocks

    def _build_payload(self, request: GenerationRequest, model: str, *, stream: bool) -> dict[str, Any]:
        system, rest = self._split_system(request.messages)
        payload: dict[str, Any] = {
            "model": model,
            "max_tokens": request.max_tokens or _DEFAULT_MAX_TOKENS,
            "messages": [{"role": m.role.value, "content": self._serialize_content(m)} for m in rest],
            "temperature": request.temperature,
            "top_p": request.top_p,
            "stream": stream,
        }
        if system:
            payload["system"] = system
        if request.stop:
            payload["stop_sequences"] = request.stop
        if request.tools:
            payload["tools"] = [
                {"name": t.name, "description": t.description, "input_schema": t.parameters} for t in request.tools
            ]
            if request.tool_choice == "auto":
                payload["tool_choice"] = {"type": "auto"}
            elif request.tool_choice == "required":
                payload["tool_choice"] = {"type": "any"}
            elif request.tool_choice not in ("none",):
                payload["tool_choice"] = {"type": "tool", "name": request.tool_choice}
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
        payload = self._build_payload(request, model, stream=False)
        try:
            resp = await self._client.post(f"{self.base_url}/v1/messages", headers=self._headers(), json=payload)
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(str(exc), provider=self.provider_name) from exc
        self._raise_for_status(resp)
        data = resp.json()
        latency_ms = (time.perf_counter() - started) * 1000
        text_parts = []
        tool_calls = []
        for block in data.get("content", []):
            if block["type"] == "text":
                text_parts.append(block["text"])
            elif block["type"] == "tool_use":
                tool_calls.append(ToolCall(id=block["id"], name=block["name"], arguments=block.get("input", {})))
        usage_raw = data.get("usage", {}) or {}
        return GenerationResponse(
            content="".join(text_parts),
            tool_calls=tool_calls,
            finish_reason=_STOP_REASON_MAP.get(data.get("stop_reason"), FinishReason.STOP),
            usage=TokenUsage(input_tokens=usage_raw.get("input_tokens", 0), output_tokens=usage_raw.get("output_tokens", 0)),
            execution=ExecutionMetadata(request_id=request.request_id, provider=self.provider_name, model=model, latency_ms=latency_ms),
        )

    async def stream(self, request: GenerationRequest, *, model: str) -> AsyncIterator[StreamChunk]:
        payload = self._build_payload(request, model, stream=True)
        try:
            async with self._client.stream("POST", f"{self.base_url}/v1/messages", headers=self._headers(), json=payload) as resp:
                if resp.status_code >= 400:
                    await resp.aread()
                    self._raise_for_status(resp)
                event_name = None
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("event:"):
                        event_name = line[len("event:"):].strip()
                        continue
                    if not line.startswith("data:"):
                        continue
                    data = json.loads(line[len("data:"):].strip())
                    if event_name == "content_block_delta":
                        delta = data.get("delta", {})
                        if delta.get("type") == "text_delta":
                            yield StreamChunk(request_id=request.request_id, delta=delta.get("text", ""))
                        elif delta.get("type") == "input_json_delta":
                            yield StreamChunk(
                                request_id=request.request_id,
                                tool_call_delta={"partial_json": delta.get("partial_json", "")},
                            )
                    elif event_name == "message_delta":
                        stop_reason = data.get("delta", {}).get("stop_reason")
                        usage_raw = data.get("usage", {}) or {}
                        yield StreamChunk(
                            request_id=request.request_id,
                            finish_reason=_STOP_REASON_MAP.get(stop_reason) if stop_reason else None,
                            usage=TokenUsage(output_tokens=usage_raw.get("output_tokens", 0)) if usage_raw else None,
                            is_final=stop_reason is not None,
                        )
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError(str(exc), provider=self.provider_name) from exc

    async def health_check(self) -> bool:
        # Anthropic has no dedicated health endpoint; a minimal 1-token
        # request is expensive to run just for liveness, so we treat
        # "client constructed with an API key" as healthy and rely on the
        # execution engine's real-request failures to mark it degraded.
        return bool(self.api_key)
