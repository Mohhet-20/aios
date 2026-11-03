"""HttpClientHandler: a real HTTP call via httpx — no mocking, no fake
response synthesis; a misconfigured URL fails exactly like it would in
production. Backs `connector_key="http_client"`, which the category
registry (`tool_registry/registry.py`) wires up for HTTP_CLIENT,
REST_API, GRAPHQL_API, CRM, ERP, and CUSTOM_ENTERPRISE_API — every one
of those categories is, mechanically, "call an HTTP endpoint with some
auth," differing only in `config`/`input_data` shape, not in handler
code. `ctx.network_policy`, when set, is checked before every request —
this is the enforcement point `sandbox/network_policy.py`'s allow-list
actually protects."""
from __future__ import annotations

from typing import Any

import httpx

from tool_platform.core.exceptions import ToolExecutionError
from tool_platform.credentials.token_injection import build_auth_headers
from tool_platform.tool_execution.context import ToolCallContext
from tool_platform.tool_execution.handlers.base import ConnectorHandler


class HttpClientHandler(ConnectorHandler):
    def __init__(self, *, client: httpx.AsyncClient | None = None):
        self._client = client

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        if self._client is not None:
            return await self._client.request(method, url, **kwargs)
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await client.request(method, url, **kwargs)

    def _resolve_auth_headers(self, ctx: ToolCallContext) -> dict[str, str]:
        if not ctx.credential_secret:
            return {}
        credential_type = ctx.config.get("credential_type") or ctx.input_data.get("credential_type")
        if not credential_type:
            return {}
        return build_auth_headers(credential_type, ctx.credential_secret)

    async def execute(self, ctx: ToolCallContext) -> dict[str, Any]:
        method = (ctx.config.get("method") or ctx.input_data.get("method") or "GET").upper()
        url = ctx.config.get("url") or ctx.input_data.get("url")
        if not url:
            raise ToolExecutionError("http_client tool call requires a 'url' in config or input_data")

        if ctx.network_policy is not None:
            ctx.network_policy.check_url(url)

        headers = {**(ctx.config.get("headers") or {}), **self._resolve_auth_headers(ctx)}
        response = await self._request(
            method, url, headers=headers, params=ctx.input_data.get("params") or ctx.config.get("params"),
            json=ctx.input_data.get("body") or ctx.config.get("body"),
        )
        try:
            body: Any = response.json()
        except Exception:
            body = response.text
        return {"status_code": response.status_code, "body": body, "network_bytes": len(response.content)}

    async def compensate(self, ctx: ToolCallContext) -> None:
        compensate_url = ctx.config.get("compensate_url")
        if not compensate_url:
            return
        await self._request(ctx.config.get("compensate_method", "POST"), compensate_url, json=ctx.config.get("compensate_body"))
