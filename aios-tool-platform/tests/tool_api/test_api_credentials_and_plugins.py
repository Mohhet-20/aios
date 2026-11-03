import pytest


async def _make_workspace(client, name="Cred Co", slug="cred-co"):
    r = await client.post("/api/v1/workspaces", json={"name": name, "slug": slug, "organization_id": "org-1"})
    assert r.status_code == 201
    return r.json()


@pytest.mark.asyncio
async def test_credential_lifecycle_via_api(client):
    ws = await _make_workspace(client)
    r = await client.post("/api/v1/credentials", json={
        "workspace_id": ws["id"], "name": "Slack Token", "credential_type": "api_key",
        "secret_material": {"key": "sk-abc123"}, "owner_id": "u1",
    })
    assert r.status_code == 201, r.text
    cred = r.json()
    assert "sk-abc123" not in str(cred)  # ciphertext only, never the plaintext secret

    r = await client.get("/api/v1/credentials", params={"workspace_id": ws["id"]})
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = await client.post(f"/api/v1/credentials/{cred['id']}/rotate", json={"new_secret_material": {"key": "sk-new456"}})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "active"

    r = await client.post(f"/api/v1/credentials/{cred['id']}/revoke")
    assert r.status_code == 200
    assert r.json()["status"] == "revoked"


@pytest.mark.asyncio
async def test_plugin_marketplace_and_installation_flow(client):
    ws = await _make_workspace(client, name="Plugin Co", slug="plugin-co")

    r = await client.post("/api/v1/plugins", json={
        "name": "Slack Connector", "author": "acme", "category": "custom",
        "manifest": {"capabilities": ["network_access"]},
    })
    assert r.status_code == 201, r.text
    plugin = r.json()
    assert plugin["is_signed"] is True

    r = await client.get("/api/v1/marketplace/search", params={"query": "Slack"})
    assert r.status_code == 200
    assert any(p["id"] == plugin["id"] for p in r.json())

    r = await client.post("/api/v1/installations", json={
        "workspace_id": ws["id"], "plugin_id": plugin["id"], "installed_by": "u1",
    })
    assert r.status_code == 201, r.text
    installation = r.json()
    assert installation["status"] == "installed"

    r = await client.post(f"/api/v1/installations/{installation['id']}/enable")
    assert r.status_code == 200
    assert r.json()["status"] == "enabled"

    r = await client.get("/api/v1/marketplace/most-installed")
    assert r.status_code == 200
    assert any(p["id"] == plugin["id"] for p in r.json())
