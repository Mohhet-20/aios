"""POST /api/v1/auth/guest: the public demo's passwordless session for an ordinary member, never an administrator."""
import jwt
import pytest

from identity_platform.config.settings import get_settings

pytestmark = pytest.mark.asyncio

PASSWORD = "Str0ng!Passw0rd#1"


async def _verified_user(client, email: str) -> str:
    reg = (await client.post("/api/v1/auth/register", json={"email": email, "password": PASSWORD})).json()
    await client.post("/api/v1/auth/verify-email", json={"token": reg["verification_token"]})
    return reg["user"]["id"]


async def _org_with_member(client, owner_email: str, member_email: str) -> tuple[str, str, str]:
    owner_id = await _verified_user(client, owner_email)
    org = (await client.post("/api/v1/organizations", json={"name": f"Org {owner_email}", "owner_user_id": owner_id})).json()
    member_id = await _verified_user(client, member_email)
    added = await client.post(f"/api/v1/memberships/organizations/{org['id']}", json={"user_id": member_id})
    assert added.status_code == 201, added.text
    return org["id"], owner_id, member_id


@pytest.fixture
def guest_env(monkeypatch):
    def apply(email: str, enabled: str = "true"):
        monkeypatch.setenv("GUEST_ACCESS_ENABLED", enabled)
        monkeypatch.setenv("GUEST_EMAIL", email)
        get_settings.cache_clear()

    yield apply
    get_settings.cache_clear()


async def test_guest_access_is_off_by_default(client):
    assert (await client.post("/api/v1/auth/guest", json={})).status_code == 404


async def test_guest_gets_a_session_in_the_organisation_it_belongs_to(client, guest_env):
    org_id, _, member_id = await _org_with_member(client, "guest-owner@example.com", "guest-member@example.com")
    guest_env("guest-member@example.com")
    resp = await client.post("/api/v1/auth/guest", json={})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    claims = jwt.decode(body["access_token"], get_settings().secret_key, algorithms=["HS256"])
    assert claims["sub"] == member_id and claims["sid"] == body["session"]["id"]
    assert body["session"]["organization_id"] == org_id and body["refresh_token"]


async def test_an_organisation_owner_is_never_signed_in_as_the_guest(client, guest_env):
    await _org_with_member(client, "guest-owner2@example.com", "guest-member2@example.com")
    guest_env("guest-owner2@example.com")
    resp = await client.post("/api/v1/auth/guest", json={})
    assert resp.status_code == 403 and "access_token" not in resp.text


async def test_an_unknown_or_unverified_guest_account_is_not_found(client, guest_env):
    guest_env("nobody@example.com")
    assert (await client.post("/api/v1/auth/guest", json={})).status_code == 404
    await client.post("/api/v1/auth/register", json={"email": "guest-unverified@example.com", "password": PASSWORD})
    guest_env("guest-unverified@example.com")
    assert (await client.post("/api/v1/auth/guest", json={})).status_code == 404
