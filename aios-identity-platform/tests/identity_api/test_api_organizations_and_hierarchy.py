import pytest

pytestmark = pytest.mark.asyncio

STRONG_PASSWORD = "Str0ng!Passw0rd#1"


async def _register_user(client, email: str) -> str:
    resp = await client.post("/api/v1/auth/register", json={"email": email, "password": STRONG_PASSWORD})
    return resp.json()["user"]["id"]


async def test_organization_workspace_team_project_flow(client):
    owner_id = await _register_user(client, "api-org-owner@example.com")

    org_resp = await client.post("/api/v1/organizations", json={"name": "API Org Co", "owner_user_id": owner_id})
    assert org_resp.status_code == 201
    org = org_resp.json()
    assert org["slug"] == "api-org-co"

    get_resp = await client.get(f"/api/v1/organizations/{org['id']}")
    assert get_resp.status_code == 200

    ws_resp = await client.post("/api/v1/workspaces", json={"organization_id": org["id"], "name": "API Workspace"})
    assert ws_resp.status_code == 201
    workspace = ws_resp.json()

    team_resp = await client.post("/api/v1/teams", json={"organization_id": org["id"], "name": "API Team", "workspace_id": workspace["id"]})
    assert team_resp.status_code == 201

    project_resp = await client.post("/api/v1/projects", json={"workspace_id": workspace["id"], "name": "API Project"})
    assert project_resp.status_code == 201
    project = project_resp.json()
    assert project["organization_id"] == org["id"]

    list_ws_resp = await client.get("/api/v1/workspaces", params={"organization_id": org["id"]})
    assert len(list_ws_resp.json()) == 1


async def test_membership_and_invitation_flow(client):
    owner_id = await _register_user(client, "api-invite-owner@example.com")
    invitee_id = await _register_user(client, "api-invitee@example.com")

    org_resp = await client.post("/api/v1/organizations", json={"name": "Invite API Co", "owner_user_id": owner_id})
    org_id = org_resp.json()["id"]

    invite_resp = await client.post("/api/v1/invitations", json={
        "organization_id": org_id, "email": "api-invitee@example.com", "invited_by": owner_id,
    })
    assert invite_resp.status_code == 201
    token = invite_resp.json()["token"]

    accept_resp = await client.post("/api/v1/invitations/accept", json={"token": token, "user_id": invitee_id})
    assert accept_resp.status_code == 200
    assert accept_resp.json()["status"] == "accepted"

    members_resp = await client.get(f"/api/v1/memberships/organizations/{org_id}")
    assert members_resp.status_code == 200
    assert len(members_resp.json()) == 2


async def test_group_membership_flow(client):
    owner_id = await _register_user(client, "api-group-owner@example.com")
    member_id = await _register_user(client, "api-group-member@example.com")

    org_resp = await client.post("/api/v1/organizations", json={"name": "Group API Co", "owner_user_id": owner_id})
    org_id = org_resp.json()["id"]

    group_resp = await client.post("/api/v1/groups", json={"organization_id": org_id, "name": "API Group"})
    assert group_resp.status_code == 201
    group_id = group_resp.json()["id"]

    add_resp = await client.post(f"/api/v1/groups/{group_id}/members", json={"user_id": member_id})
    assert add_resp.status_code == 201

    members_resp = await client.get(f"/api/v1/groups/{group_id}/members")
    assert len(members_resp.json()) == 1


async def test_tenancy_usage_and_tier(client):
    owner_id = await _register_user(client, "api-tenancy-owner@example.com")
    org_resp = await client.post("/api/v1/organizations", json={"name": "Tenancy API Co", "owner_user_id": owner_id})
    org_id = org_resp.json()["id"]

    usage_resp = await client.get(f"/api/v1/tenancy/organizations/{org_id}/usage")
    assert usage_resp.status_code == 200
    assert usage_resp.json()["seat_count"] == 1

    tier_resp = await client.post(f"/api/v1/tenancy/organizations/{org_id}/tier", json={"new_tier": "enterprise"})
    assert tier_resp.status_code == 200
    assert tier_resp.json()["tenant_tier"] == "enterprise"
