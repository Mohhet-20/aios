import json

import httpx
import pytest

from aios_dev_sdk import (
    AiosDevClient,
    AiosNotFoundError,
    AiosRateLimitError,
    AiosServerError,
    ApiKey,
    Page,
)
from aios_dev_sdk.client import AsyncAiosDevClient


def test_successful_request_and_typed_model():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer dpk_test123"
        return httpx.Response(
            200,
            json={
                "id": "key-1", "name": "ci", "key_prefix": "dpk_abcd", "scopes": ["read"],
                "status": "active", "rate_limit_per_minute": 60,
            },
        )

    transport = httpx.MockTransport(handler)
    with AiosDevClient("https://api.example.com", api_key="dpk_test123", transport=transport) as client:
        response = client.request("GET", "/v1/api-keys/key-1")
        api_key = ApiKey.from_dict(response.json())
        assert api_key.id == "key-1"
        assert api_key.scopes == ["read"]


def test_404_raises_not_found_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"detail": "API key not found"})

    transport = httpx.MockTransport(handler)
    with AiosDevClient("https://api.example.com", transport=transport) as client:
        with pytest.raises(AiosNotFoundError) as exc_info:
            client.request("GET", "/v1/api-keys/missing")
        assert exc_info.value.status_code == 404


def test_retries_5xx_then_succeeds():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 3:
            return httpx.Response(503, json={"detail": "temporarily unavailable"})
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    with AiosDevClient("https://api.example.com", max_retries=3, transport=transport) as client:
        response = client.request("GET", "/v1/health")
        assert response.json() == {"ok": True}
        assert calls["count"] == 3


def test_exhausts_retries_and_raises_server_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "boom"})

    transport = httpx.MockTransport(handler)
    with AiosDevClient("https://api.example.com", max_retries=2, transport=transport) as client:
        with pytest.raises(AiosServerError):
            client.request("GET", "/v1/health")


def test_rate_limit_retries_honoring_retry_after():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, json={"detail": "slow down"}, headers={"Retry-After": "0.01"})
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    with AiosDevClient("https://api.example.com", max_retries=2, transport=transport) as client:
        response = client.request("GET", "/v1/api-keys")
        assert response.json() == {"ok": True}
        assert calls["count"] == 2


def test_rate_limit_exhausted_raises():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"detail": "slow down"})

    transport = httpx.MockTransport(handler)
    with AiosDevClient("https://api.example.com", max_retries=1, transport=transport) as client:
        with pytest.raises(AiosRateLimitError):
            client.request("GET", "/v1/api-keys")


def test_pagination_walks_all_pages():
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        if page == 1:
            return httpx.Response(200, json={"items": [{"id": "1"}, {"id": "2"}], "total": 3, "page": 1, "page_size": 2})
        return httpx.Response(200, json={"items": [{"id": "3"}], "total": 3, "page": 2, "page_size": 2})

    transport = httpx.MockTransport(handler)
    with AiosDevClient("https://api.example.com", transport=transport) as client:
        ids = [item["id"] for item in client.paginate("/v1/plugins", item_factory=lambda d: d, page_size=2)]
        assert ids == ["1", "2", "3"]


def test_streaming_yields_events():
    def handler(request: httpx.Request) -> httpx.Response:
        body = "\n".join(
            json.dumps({"event": "progress", "data": {"pct": i}}) for i in (10, 50, 100)
        )
        return httpx.Response(200, content=body.encode())

    transport = httpx.MockTransport(handler)
    with AiosDevClient("https://api.example.com", transport=transport) as client:
        events = list(client.stream("/v1/codegen/jobs/job-1/events"))
        assert [e.data["pct"] for e in events] == [10, 50, 100]
        assert all(e.event_type == "progress" for e in events)


@pytest.mark.asyncio
async def test_async_client_request_and_retry():
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 2:
            return httpx.Response(503, json={"detail": "unavailable"})
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    async with AsyncAiosDevClient("https://api.example.com", max_retries=2, transport=transport) as client:
        response = await client.request("GET", "/v1/health")
        assert response.json() == {"ok": True}
        assert calls["count"] == 2


@pytest.mark.asyncio
async def test_async_pagination():
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params.get("page", "1"))
        if page == 1:
            return httpx.Response(200, json={"items": [{"id": "a"}], "total": 2, "page": 1, "page_size": 1})
        return httpx.Response(200, json={"items": [{"id": "b"}], "total": 2, "page": 2, "page_size": 1})

    transport = httpx.MockTransport(handler)
    async with AsyncAiosDevClient("https://api.example.com", transport=transport) as client:
        ids = [item["id"] async for item in client.paginate("/v1/plugins", item_factory=lambda d: d, page_size=1)]
        assert ids == ["a", "b"]


@pytest.mark.asyncio
async def test_async_streaming():
    def handler(request: httpx.Request) -> httpx.Response:
        body = "\n".join(json.dumps({"event": "tick", "data": {"n": i}}) for i in range(3))
        return httpx.Response(200, content=body.encode())

    transport = httpx.MockTransport(handler)
    async with AsyncAiosDevClient("https://api.example.com", transport=transport) as client:
        events = [e async for e in client.stream("/v1/events")]
        assert [e.data["n"] for e in events] == [0, 1, 2]


def test_page_dataclass_pagination_math():
    page = Page.from_dict({"items": [1, 2, 3], "total": 10, "page": 1, "page_size": 3}, lambda x: x)
    assert page.total_pages == 4
    assert page.has_next is True
