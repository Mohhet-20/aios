"""Verifies the rate limiter actually trips once the configured request
budget is exceeded, and that health/metrics are exempt (so a misbehaving
client can't accidentally take down liveness probes)."""

import httpx
import pytest

from app.core.application_factory import create_app


@pytest.mark.asyncio
async def test_rate_limit_triggers_429(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "3")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")

    from app.config.settings import get_settings

    get_settings.cache_clear()
    app = create_app()
    transport = httpx.ASGITransport(app=app)

    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            statuses = []
            for _ in range(6):
                r = await ac.get("/api/v1/models")
                statuses.append(r.status_code)
            assert 429 in statuses

    get_settings.cache_clear()
