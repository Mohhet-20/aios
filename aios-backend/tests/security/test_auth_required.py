"""Security tests: endpoints behind `require_permission`/`get_current_principal`
must reject requests with no credentials, a malformed token, or an expired/
tampered token — before any business logic runs.
"""

import pytest


@pytest.mark.asyncio
async def test_protected_endpoint_rejects_missing_credentials(client):
    r = await client.post(
        "/api/v1/agents", json={"workspace_id": "ws1", "name": "A", "role": "R", "model_id": "m"}
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_protected_endpoint_rejects_garbage_token(client):
    r = await client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-jwt"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_invalid_api_key_rejected(client):
    r = await client.get("/api/v1/auth/me", headers={"X-API-Key": "sk_live_not-a-real-key"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_health_and_metrics_do_not_require_auth(client):
    r = await client.get("/health/live")
    assert r.status_code == 200
    r = await client.get("/metrics")
    assert r.status_code == 200
