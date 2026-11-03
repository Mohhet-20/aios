"""The service edge guard: internal token on every non-health route, fail-closed production config, opt-in CORS."""
import httpx
import pytest

from identity_platform.identity_api.application_factory import create_app

pytestmark = pytest.mark.asyncio

TOKEN = "t" * 40


def _client(app) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_routes_require_the_internal_token_when_configured(monkeypatch):
    monkeypatch.setenv("AIOS_INTERNAL_TOKEN", TOKEN)
    async with _client(create_app()) as client:
        assert (await client.get("/health/live")).status_code == 200  # orchestrator probes stay open
        missing = await client.post("/api/v1/auth/token", json={"email": "a@b.c", "password": "x"})
        assert missing.status_code == 401 and "internal service token" in missing.json()["detail"]
        wrong = await client.get("/openapi.json", headers={"X-Internal-Token": "t" * 39 + "u"})
        assert wrong.status_code == 401
        ok = await client.get("/openapi.json", headers={"X-Internal-Token": TOKEN})
        assert ok.status_code == 200


async def test_open_when_no_token_is_configured(monkeypatch):
    monkeypatch.delenv("AIOS_INTERNAL_TOKEN", raising=False)
    async with _client(create_app()) as client:
        assert (await client.get("/openapi.json")).status_code == 200


async def test_production_refuses_to_start_without_a_strong_token(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AIOS_INTERNAL_TOKEN", "short")
    with pytest.raises(RuntimeError, match="AIOS_INTERNAL_TOKEN"):
        create_app()


async def test_cors_is_off_unless_origins_are_listed(monkeypatch):
    monkeypatch.delenv("AIOS_INTERNAL_TOKEN", raising=False)
    preflight = {"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}
    monkeypatch.delenv("AIOS_CORS_ORIGINS", raising=False)
    async with _client(create_app()) as client:
        resp = await client.options("/health", headers=preflight)
        assert "access-control-allow-origin" not in resp.headers
    monkeypatch.setenv("AIOS_CORS_ORIGINS", "https://console.example")
    async with _client(create_app()) as client:
        allowed = await client.options("/health", headers={**preflight, "Origin": "https://console.example"})
        assert allowed.headers.get("access-control-allow-origin") == "https://console.example"
        denied = await client.options("/health", headers=preflight)
        assert denied.headers.get("access-control-allow-origin") != "https://evil.example"
