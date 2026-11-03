import pytest

pytestmark = pytest.mark.asyncio

STRONG_PASSWORD = "Str0ng!Passw0rd#1"


async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
@pytest.mark.asyncio
async def test_health_liveness_probe(client):
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    assert resp.json() == {"status": "alive"}


@pytest.mark.asyncio
async def test_health_readiness_probe(client):
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["components"][0]["name"] == "database"
    assert body["components"][0]["healthy"] is True



async def test_register_verify_login_flow(client):
    register_resp = await client.post("/api/v1/auth/register", json={
        "email": "api-auth@example.com", "password": STRONG_PASSWORD,
    })
    assert register_resp.status_code == 201
    body = register_resp.json()
    assert body["user"]["email"] == "api-auth@example.com"
    verification_token = body["verification_token"]

    verify_resp = await client.post("/api/v1/auth/verify-email", json={"token": verification_token})
    assert verify_resp.status_code == 200
    assert verify_resp.json()["status"] == "active"

    login_resp = await client.post("/api/v1/auth/login", json={"email": "api-auth@example.com", "password": STRONG_PASSWORD})
    assert login_resp.status_code == 200
    assert login_resp.json()["status"] == "active"


async def test_login_with_wrong_password_returns_401(client):
    await client.post("/api/v1/auth/register", json={"email": "api-wrongpw@example.com", "password": STRONG_PASSWORD})

    resp = await client.post("/api/v1/auth/login", json={"email": "api-wrongpw@example.com", "password": "not-the-password"})
    assert resp.status_code == 401
    assert resp.json()["error"] == "InvalidCredentialsError"


async def test_register_duplicate_email_returns_409(client):
    await client.post("/api/v1/auth/register", json={"email": "api-dupe@example.com", "password": STRONG_PASSWORD})
    resp = await client.post("/api/v1/auth/register", json={"email": "api-dupe@example.com", "password": STRONG_PASSWORD})
    assert resp.status_code == 409


async def test_password_reset_flow(client):
    await client.post("/api/v1/auth/register", json={"email": "api-reset@example.com", "password": STRONG_PASSWORD})

    reset_req = await client.post("/api/v1/auth/request-password-reset", json={"email": "api-reset@example.com"})
    assert reset_req.status_code == 200
    reset_token = reset_req.json()["reset_token"]
    assert reset_token

    new_password = "N3w!Str0ngPassw0rd#9"
    reset_resp = await client.post("/api/v1/auth/reset-password", json={"token": reset_token, "new_password": new_password})
    assert reset_resp.status_code == 200
