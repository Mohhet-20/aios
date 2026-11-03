"""Reference HTTP client for the AIOS Enterprise Developer Platform
API: sync + async variants, both built on `httpx` with the same
request-building/error-mapping/retry logic so behavior never drifts
between them. `transport=` on either constructor exists so this SDK's
own test suite (and any consumer's tests) can swap in
`httpx.MockTransport` instead of a real socket — no live server
required to exercise retry/pagination/streaming/error-mapping logic."""
from __future__ import annotations

import asyncio
import json as json_lib
import time
from collections.abc import AsyncIterator, Iterator
from typing import Any, Callable

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from aios_dev_sdk.errors import AiosConnectionError, AiosRateLimitError, AiosServerError, error_for_status
from aios_dev_sdk.models import Page, StreamEvent

_RETRYABLE = (AiosServerError, AiosConnectionError)
_MAX_BACKOFF_SECONDS = 0.5


def _raise_for_response(response: httpx.Response) -> None:
    if response.status_code < 400:
        return
    try:
        body = response.json()
    except ValueError:
        body = response.text
    message = body.get("detail") if isinstance(body, dict) else str(body)
    message = message or f"HTTP {response.status_code}"
    retry_after = None
    if response.status_code == 429:
        header = response.headers.get("Retry-After")
        if header is not None:
            try:
                retry_after = float(header)
            except ValueError:
                retry_after = None
    raise error_for_status(response.status_code, message=message, body=body, retry_after_seconds=retry_after)


def _rate_limit_wait(exc: AiosRateLimitError, attempt: int) -> float:
    if exc.retry_after_seconds is not None:
        return exc.retry_after_seconds
    return min(0.01 * (2**attempt), _MAX_BACKOFF_SECONDS)


class AiosDevClient:
    """Synchronous reference client."""

    def __init__(
        self, base_url: str, api_key: str | None = None, *, timeout: float = 10.0,
        max_retries: int = 3, transport: httpx.BaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.max_retries = max_retries
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout, headers=headers, transport=transport)
        self._retrying_send: Callable[..., httpx.Response] = retry(
            retry=retry_if_exception_type(_RETRYABLE),
            stop=stop_after_attempt(max_retries + 1),
            wait=wait_exponential(multiplier=0.01, max=_MAX_BACKOFF_SECONDS),
            reraise=True,
        )(self._send_once)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "AiosDevClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _send_once(self, method: str, path: str, *, json: Any = None, params: dict | None = None) -> httpx.Response:
        try:
            response = self._client.request(method, path, json=json, params=params)
        except httpx.TransportError as exc:
            raise AiosConnectionError(str(exc)) from exc
        _raise_for_response(response)
        return response

    def request(self, method: str, path: str, *, json: Any = None, params: dict | None = None) -> httpx.Response:
        """Retries 5xx/connection failures with exponential backoff
        (via tenacity), and separately retries 429s honoring the
        server's `Retry-After` header when present — both bounded by
        `max_retries`, after which the original error propagates."""
        attempt = 0
        while True:
            try:
                return self._retrying_send(method, path, json=json, params=params)
            except AiosRateLimitError as exc:
                attempt += 1
                if attempt > self.max_retries:
                    raise
                time.sleep(_rate_limit_wait(exc, attempt))

    def paginate(self, path: str, *, item_factory: Callable[[dict], Any], params: dict | None = None, page_size: int = 50) -> Iterator[Any]:
        page_num = 1
        base_params = dict(params or {})
        while True:
            query = dict(base_params)
            query["page"] = page_num
            query["page_size"] = page_size
            response = self.request("GET", path, params=query)
            page = Page.from_dict(response.json(), item_factory)
            yield from page.items
            if not page.has_next:
                return
            page_num += 1

    def stream(self, path: str, *, params: dict | None = None) -> Iterator[StreamEvent]:
        with self._client.stream("GET", path, params=params) as response:
            _raise_for_response(response)
            for line in response.iter_lines():
                if not line:
                    continue
                payload = json_lib.loads(line)
                yield StreamEvent(event_type=payload.get("event", "message"), data=payload.get("data", payload))


class AsyncAiosDevClient:
    """Async reference client — identical request/error/retry
    semantics to `AiosDevClient`, built on `httpx.AsyncClient`."""

    def __init__(
        self, base_url: str, api_key: str | None = None, *, timeout: float = 10.0,
        max_retries: int = 3, transport: httpx.AsyncBaseTransport | None = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.max_retries = max_retries
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=timeout, headers=headers, transport=transport)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncAiosDevClient":
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def _send_once(self, method: str, path: str, *, json: Any = None, params: dict | None = None) -> httpx.Response:
        try:
            response = await self._client.request(method, path, json=json, params=params)
        except httpx.TransportError as exc:
            raise AiosConnectionError(str(exc)) from exc
        _raise_for_response(response)
        return response

    async def request(self, method: str, path: str, *, json: Any = None, params: dict | None = None) -> httpx.Response:
        attempt = 0
        while True:
            try:
                return await self._send_once(method, path, json=json, params=params)
            except _RETRYABLE:
                attempt += 1
                if attempt > self.max_retries:
                    raise
                await asyncio.sleep(min(0.01 * (2**attempt), _MAX_BACKOFF_SECONDS))
            except AiosRateLimitError as exc:
                attempt += 1
                if attempt > self.max_retries:
                    raise
                await asyncio.sleep(_rate_limit_wait(exc, attempt))

    async def paginate(
        self, path: str, *, item_factory: Callable[[dict], Any], params: dict | None = None, page_size: int = 50,
    ) -> AsyncIterator[Any]:
        page_num = 1
        base_params = dict(params or {})
        while True:
            query = dict(base_params)
            query["page"] = page_num
            query["page_size"] = page_size
            response = await self.request("GET", path, params=query)
            page = Page.from_dict(response.json(), item_factory)
            for item in page.items:
                yield item
            if not page.has_next:
                return
            page_num += 1

    async def stream(self, path: str, *, params: dict | None = None) -> AsyncIterator[StreamEvent]:
        async with self._client.stream("GET", path, params=params) as response:
            _raise_for_response(response)
            async for line in response.aiter_lines():
                if not line:
                    continue
                payload = json_lib.loads(line)
                yield StreamEvent(event_type=payload.get("event", "message"), data=payload.get("data", payload))
