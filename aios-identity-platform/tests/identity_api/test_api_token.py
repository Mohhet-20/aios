"""POST /api/v1/auth/token: password (and MFA when enrolled) in, session tokens out."""
import jwt
import pytest

from identity_platform.config.settings import get_settings
from identity_platform.security.totp import generate_totp

pytestmark = pytest.mark.asyncio

PASSWORD = "Str0ng!Passw0rd#1"


async def _verified_user(client, email: str) -> str:
    reg = (await client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})).json()
    await client.post("/api/v1/auth/verify-email", json={"token": reg["verification_token"]})
    return reg["user"]["id"]


async def test_token_issues_a_session_for_valid_credentials(client):
    user_id = await _verified_user(client, "token-ok@example.com")
    resp = await client.post("/api/v1/auth/token", json={"email": "token-ok@example.com", "password": PASSWORD})
    assert resp.status_code == 200
    body = resp.json()
    assert body["user"]["id"] == user_id
    claims = jwt.decode(body["access_token"], get_settings().secret_key, algorithms=["HS256"])
    assert claims["sub"] == user_id and claims["sid"] == body["session"]["id"]
    assert body["refresh_token"]


async def test_token_rejects_a_wrong_password(client):
    await _verified_user(client, "token-badpw@example.com")
    resp = await client.post("/api/v1/auth/token", json={"email": "token-badpw@example.com", "password": "nope-Not-It-1!"})
    assert resp.status_code == 401
    assert "access_token" not in resp.text


async def test_token_rejects_an_unverified_account(client):
    await client.post("/api/v1/auth/register", json={"email": "token-unverified@example.com", "password": PASSWORD})
    resp = await client.post("/api/v1/auth/token", json={"email": "token-unverified@example.com", "password": PASSWORD})
    assert resp.status_code == 403  # same mapping as /auth/login: AccountNotVerifiedError
    assert "access_token" not in resp.text


async def test_token_requires_and_checks_the_mfa_code_when_enrolled(client):
    user_id = await _verified_user(client, "token-mfa@example.com")
    enrollment = (await client.post("/api/v1/mfa/totp/enroll", json={"user_id": user_id, "account_email": "token-mfa@example.com"})).json()
    await client.post("/api/v1/mfa/totp/confirm", json={"factor_id": enrollment["factor_id"], "code": generate_totp(enrollment["raw_secret"])})
    creds = {"email": "token-mfa@example.com", "password": PASSWORD}

    missing = await client.post("/api/v1/auth/token", json=creds)
    assert missing.status_code == 401 and missing.json()["error"] == "MfaRequiredError"
    assert "access_token" not in missing.text

    wrong = await client.post("/api/v1/auth/token", json={**creds, "mfa_code": "000000"})
    assert wrong.status_code == 401 and wrong.json()["error"] == "InvalidMfaCodeError"

    ok = await client.post("/api/v1/auth/token", json={**creds, "mfa_code": generate_totp(enrollment["raw_secret"])})
    assert ok.status_code == 200 and ok.json()["access_token"]
