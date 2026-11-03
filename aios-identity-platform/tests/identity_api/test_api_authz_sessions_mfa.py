import pytest

from identity_platform.authorization.bootstrap import seed_builtin_roles

pytestmark = pytest.mark.asyncio

STRONG_PASSWORD = "Str0ng!Passw0rd#1"


async def _register_user(client, email: str) -> str:
    resp = await client.post("/api/v1/auth/register", json={"email": email, "password": STRONG_PASSWORD})
    return resp.json()["user"]["id"]


async def test_authorization_check_for_org_owner(client, repos, db_session):
    # Explicitly seed rather than relying on another test module having
    # already done so — this file must pass in isolation, not just as
    # part of the full suite.
    await seed_builtin_roles(repos)
    await db_session.commit()

    owner_id = await _register_user(client, "api-authz-owner@example.com")
    org_resp = await client.post("/api/v1/organizations", json={"name": "Authz API Co", "owner_user_id": owner_id})
    org_id = org_resp.json()["id"]

    check_resp = await client.get("/api/v1/authorization/check", params={
        "principal_type": "user", "principal_id": owner_id, "permission_key": "workspace:create",
        "scope_type": "organization", "scope_id": org_id,
    })
    assert check_resp.status_code == 200
    assert check_resp.json()["allowed"] is True

    effective_resp = await client.get("/api/v1/authorization/effective-permissions", params={
        "principal_type": "user", "principal_id": owner_id, "scope_type": "organization", "scope_id": org_id,
    })
    assert effective_resp.status_code == 200
    assert len(effective_resp.json()["permissions"]) > 0


async def test_session_create_refresh_revoke_flow(client):
    user_id = await _register_user(client, "api-session-user@example.com")

    create_resp = await client.post("/api/v1/sessions", json={"user_id": user_id})
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["access_token"]
    refresh_token = body["refresh_token"]
    session_id = body["session"]["id"]

    refresh_resp = await client.post("/api/v1/sessions/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 200
    new_refresh_token = refresh_resp.json()["refresh_token"]
    assert new_refresh_token != refresh_token

    revoke_resp = await client.post(f"/api/v1/sessions/{session_id}/revoke", json={})
    assert revoke_resp.status_code == 200
    assert revoke_resp.json()["status"] == "revoked"


async def test_mfa_enroll_confirm_and_verify_flow(client):
    from identity_platform.security.totp import generate_totp

    user_id = await _register_user(client, "api-mfa-user@example.com")

    enroll_resp = await client.post("/api/v1/mfa/totp/enroll", json={"user_id": user_id, "account_email": "api-mfa-user@example.com"})
    assert enroll_resp.status_code == 200
    enrollment = enroll_resp.json()
    code = generate_totp(enrollment["raw_secret"])

    confirm_resp = await client.post("/api/v1/mfa/totp/confirm", json={"factor_id": enrollment["factor_id"], "code": code})
    assert confirm_resp.status_code == 200
    assert len(confirm_resp.json()["recovery_codes"]) == 10

    fresh_code = generate_totp(enrollment["raw_secret"])
    verify_resp = await client.post("/api/v1/mfa/verify", json={"user_id": user_id, "code": fresh_code})
    assert verify_resp.status_code == 200
    assert verify_resp.json()["verified"] is True
