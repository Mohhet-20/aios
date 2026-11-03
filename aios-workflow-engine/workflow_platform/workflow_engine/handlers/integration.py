"""External-integration node handlers. WEBHOOK and REST_API make real
HTTP calls via httpx — no mocking, no fake response synthesis; a
misconfigured URL fails exactly like it would in production. Both
support compensation (a configured `compensate_url`/`compensate_method`)
since an outbound HTTP side effect is exactly the kind of thing a saga
rollback needs to be able to undo."""
from __future__ import annotations

from typing import Any

import httpx

from workflow_platform.core.exceptions import NodeExecutionError
from workflow_platform.workflow_engine.context import NodeContext
from workflow_platform.workflow_engine.handlers.base import NodeHandler


class RestApiHandler(NodeHandler):
    def __init__(self, *, client: httpx.AsyncClient | None = None):
        self._client = client

    async def _request(self, method: str, url: str, **kwargs) -> httpx.Response:
        if self._client is not None:
            return await self._client.request(method, url, **kwargs)
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await client.request(method, url, **kwargs)

    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        method = ctx.config.get("method", "GET").upper()
        url = ctx.config.get("url")
        if not url:
            raise NodeExecutionError("REST_API node requires a 'url' in its config")
        response = await self._request(
            method, url, headers=ctx.config.get("headers"), params=ctx.config.get("params"), json=ctx.config.get("body"),
        )
        try:
            body = response.json()
        except Exception:
            body = response.text
        return {"status_code": response.status_code, "body": body}

    async def compensate(self, ctx: NodeContext) -> None:
        compensate_url = ctx.config.get("compensate_url")
        if not compensate_url:
            return
        await self._request(ctx.config.get("compensate_method", "POST"), compensate_url, json=ctx.config.get("compensate_body"))


class WebhookHandler(NodeHandler):
    def __init__(self, *, client: httpx.AsyncClient | None = None):
        self._client = client

    async def execute(self, ctx: NodeContext) -> dict[str, Any]:
        url = ctx.config.get("url")
        if not url:
            raise NodeExecutionError("WEBHOOK node requires a 'url' in its config")
        payload = ctx.config.get("payload") or {"execution_id": ctx.execution.id, "variables": dict(ctx.variables)}
        if self._client is not None:
            response = await self._client.post(url, json=payload, headers=ctx.config.get("headers"))
        else:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, json=payload, headers=ctx.config.get("headers"))
        return {"status_code": response.status_code, "delivered": response.is_success}
