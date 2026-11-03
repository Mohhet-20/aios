import pytest


@pytest.mark.asyncio
async def test_register_login_me_flow(client):
    register_payload = {"email": "flow@aios.dev", "password": "supersecret123", "full_name": "Flow User"}
    r = await client.post("/api/v1/auth/register", json=register_payload)
    assert r.status_code == 201
    assert r.json()["email"] == "flow@aios.dev"

    r = await client.post("/api/v1/auth/login", json={"email": "flow@aios.dev", "password": "supersecret123"})
    assert r.status_code == 200
    tokens = r.json()
    assert "access_token" in tokens and "refresh_token" in tokens

    r = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"})
    assert r.status_code == 200
    assert r.json()["role"] == "member"


@pytest.mark.asyncio
async def test_duplicate_registration_conflicts(client):
    payload = {"email": "dupe@aios.dev", "password": "supersecret123", "full_name": "Dupe"}
    r1 = await client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409
    assert r2.json()["error"]["code"] == "conflict"


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(client):
    payload = {"email": "wrongpass@aios.dev", "password": "supersecret123", "full_name": "WP"}
    await client.post("/api/v1/auth/register", json=payload)
    r = await client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": "wrong-password"}
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_refresh_rotates_token(client):
    payload = {"email": "refresh@aios.dev", "password": "supersecret123", "full_name": "Refresh"}
    await client.post("/api/v1/auth/register", json=payload)
    login = await client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": payload["password"]}
    )
    old_refresh = login.json()["refresh_token"]

    r = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r.status_code == 200

    # old refresh token was rotated (single-use) — reusing it must fail
    r2 = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert r2.status_code == 401
