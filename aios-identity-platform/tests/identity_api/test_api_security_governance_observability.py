import pytest

pytestmark = pytest.mark.asyncio

STRONG_PASSWORD = "Str0ng!Passw0rd#1"


async def _register_user(client, email: str) -> str:
    resp = await client.post("/api/v1/auth/register", json={"email": email, "password": STRONG_PASSWORD})
    return resp.json()["user"]["id"]


async def test_security_policy_and_restriction_flow(client):
    policy_resp = await client.put("/api/v1/security/policies", json={
        "organization_id": "org-api-sec", "policy_type": "ip_restriction",
        "config": {"mode": "allow", "values": ["10.0.0.0/8"]},
    })
    assert policy_resp.status_code == 200

    check_resp = await client.get("/api/v1/security/restrictions/ip", params={"organization_id": "org-api-sec", "ip_address": "10.1.2.3"})
    assert check_resp.status_code == 200
    assert check_resp.json()["allowed"] is True

    blocked_resp = await client.get("/api/v1/security/restrictions/ip", params={"organization_id": "org-api-sec", "ip_address": "8.8.8.8"})
    assert blocked_resp.json()["allowed"] is False


async def test_security_event_and_risk_scoring(client):
    user_id = await _register_user(client, "api-security-user@example.com")

    event_resp = await client.post("/api/v1/security/events", json={
        "event_type": "brute_force", "severity": "warning", "user_id": user_id, "organization_id": "org-api-sec-2",
    })
    assert event_resp.status_code == 201

    unresolved_resp = await client.get("/api/v1/security/events/unresolved", params={"organization_id": "org-api-sec-2"})
    assert len(unresolved_resp.json()) == 1

    risk_resp = await client.post("/api/v1/security/risk/score", json={
        "user_id": user_id, "is_new_device": True, "is_new_country": True,
    })
    assert risk_resp.status_code == 200
    assert 0 <= risk_resp.json()["risk_score"] <= 1


async def test_api_key_issue_and_verify(client):
    owner_id = await _register_user(client, "api-key-owner@example.com")
    org_resp = await client.post("/api/v1/organizations", json={"name": "ApiKey API Co", "owner_user_id": owner_id})
    org_id = org_resp.json()["id"]

    issue_resp = await client.post("/api/v1/api-keys", json={
        "organization_id": org_id, "owner_type": "user", "owner_id": owner_id, "name": "CI Key", "created_by": owner_id,
    })
    assert issue_resp.status_code == 201
    raw_key = issue_resp.json()["raw_key"]

    verify_resp = await client.post("/api/v1/api-keys/verify", json={"raw_key": raw_key})
    assert verify_resp.status_code == 200
    assert verify_resp.json()["organization_id"] == org_id


async def test_governance_and_observability_endpoints(client):
    owner_id = await _register_user(client, "api-gov-owner@example.com")
    org_resp = await client.post("/api/v1/organizations", json={"name": "Gov API Co", "owner_user_id": owner_id})
    org_id = org_resp.json()["id"]

    audit_resp = await client.get(f"/api/v1/governance/audit-log/organizations/{org_id}")
    assert audit_resp.status_code == 200

    summary_resp = await client.get(f"/api/v1/governance/organizations/{org_id}/compliance-summary")
    assert summary_resp.status_code == 200
    assert summary_resp.json()["active_member_count"] == 1

    export_resp = await client.get(f"/api/v1/governance/users/{owner_id}/data-export")
    assert export_resp.status_code == 200
    assert export_resp.json()["profile"]["email"] == "api-gov-owner@example.com"

    metrics_resp = await client.get("/api/v1/observability/auth")
    assert metrics_resp.status_code == 200

    growth_resp = await client.get("/api/v1/observability/organization-growth", params={"since": "2020-01-01T00:00:00"})
    assert growth_resp.status_code == 200
    assert growth_resp.json()["total_organizations"] >= 1
