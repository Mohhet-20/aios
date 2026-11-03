"""Drives the platform purely through HTTP, end to end, across every
domain — the same style as every prior AIOS platform's API test
suite. Uses a dedicated tenant id (`api-e2e-tenant`, set in
conftest.py's `client` fixture) rather than the generic ids used
throughout the unit-level test suites, to keep this suite's state
isolated from those."""
from __future__ import annotations

import base64

import pytest

pytestmark = pytest.mark.asyncio


async def test_health_probe(client):
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



async def test_release_and_version_flow(client):
    resp = await client.post("/api/v1/releases", json={"version": "1.0.0", "channel": "stable"})
    assert resp.status_code == 201
    release = resp.json()
    assert release["status"] == "draft"

    resp = await client.post(f"/api/v1/releases/{release['id']}/submit-for-candidate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "candidate"

    resp = await client.post(f"/api/v1/releases/{release['id']}/approve")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/releases/{release['id']}/release")
    assert resp.status_code == 200
    assert resp.json()["status"] == "released"

    resp = await client.get(f"/api/v1/releases/{release['id']}/history")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp = await client.post("/api/v1/compatibility", json={
        "version": "1.0.0", "component_ref": "sdk:python", "compatible_from": "1.0.0", "compatible_to": "2.0.0",
    })
    assert resp.status_code == 201

    resp = await client.get("/api/v1/compatibility/1.0.0/check", params={"component_ref": "sdk:python", "candidate_version": "1.5.0"})
    assert resp.status_code == 200
    assert resp.json()["compatible"] is True


async def test_artifact_and_distribution_flow(client):
    resp = await client.post("/api/v1/artifacts", json={
        "release_id": "rel-api-1", "artifact_type": "docker_image", "name": "aios-backend", "version": "1.0.0",
    })
    assert resp.status_code == 201
    artifact = resp.json()
    assert artifact["signed"] is False

    resp = await client.get("/api/v1/artifacts/by-release/rel-api-1")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.post("/api/v1/distribution-channels", json={"channel_type": "docker_registry", "name": "api-registry-1"})
    assert resp.status_code == 201
    channel = resp.json()

    resp = await client.post("/api/v1/distribution-entries", json={"artifact_id": artifact["id"], "channel_id": channel["id"]})
    assert resp.status_code == 201
    assert resp.json()["status"] == "published"


async def test_deployment_flow(client):
    resp = await client.post("/api/v1/deployments", json={"release_id": "rel-1", "environment_id": "env-1", "target_type": "cloud"})
    assert resp.status_code == 201
    deployment = resp.json()

    resp = await client.post(f"/api/v1/deployments/{deployment['id']}/start")
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"

    resp = await client.post(f"/api/v1/deployments/{deployment['id']}/succeed")
    assert resp.status_code == 200
    assert resp.json()["status"] == "succeeded"

    resp = await client.post(f"/api/v1/deployments/{deployment['id']}/mark-rolled-back")
    assert resp.status_code == 200
    assert resp.json()["status"] == "rolled_back"


async def test_rollout_flow(client):
    resp = await client.post("/api/v1/rollouts", json={"deployment_id": "dep-1", "strategy": "canary"})
    assert resp.status_code == 201
    rollout = resp.json()

    resp = await client.post(f"/api/v1/rollouts/{rollout['id']}/start")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/rollouts/{rollout['id']}/advance-default-step")
    assert resp.status_code == 200
    assert resp.json()["current_step_pct"] == 10.0

    resp = await client.post(f"/api/v1/rollouts/{rollout['id']}/pause")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/rollouts/{rollout['id']}/resume")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/rollouts/{rollout['id']}/complete")
    assert resp.status_code == 200
    assert resp.json()["current_step_pct"] == 100.0


async def test_feature_flag_flow(client):
    resp = await client.post("/api/v1/feature-flags", json={"key": "api-flag", "name": "API Flag", "enabled": True, "rollout_pct": 100.0})
    assert resp.status_code == 201
    flag = resp.json()

    resp = await client.get(f"/api/v1/feature-flag-overrides/{flag['id']}/evaluate/user-1")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is True

    resp = await client.post("/api/v1/feature-flag-overrides", json={"flag_id": flag["id"], "target_ref": "user-2", "enabled": False})
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/feature-flag-overrides/{flag['id']}/evaluate/user-2")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False

    resp = await client.post(f"/api/v1/feature-flags/{flag['id']}/emergency-disable")
    assert resp.status_code == 200

    resp = await client.get(f"/api/v1/feature-flag-overrides/{flag['id']}/evaluate/user-1")
    assert resp.status_code == 200
    assert resp.json()["enabled"] is False


async def test_update_flow(client):
    resp = await client.post("/api/v1/update-jobs", json={"target_ref": "install:api-1", "update_type": "automatic", "to_version": "1.1.0"})
    assert resp.status_code == 201
    job = resp.json()

    resp = await client.post(f"/api/v1/update-jobs/{job['id']}/start-download")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/update-jobs/{job['id']}/begin-apply")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/update-jobs/{job['id']}/mark-applied")
    assert resp.status_code == 200
    assert resp.json()["status"] == "applied"

    await client.post("/api/v1/compatibility", json={
        "version": "9.0.0", "component_ref": "sdk:go", "compatible_from": "1.0.0", "compatible_to": "2.0.0",
    })
    resp = await client.post("/api/v1/update-jobs/check-compatibility", json={
        "platform_version": "9.0.0", "component_ref": "sdk:go", "candidate_version": "1.5.0",
    })
    assert resp.status_code == 200
    assert resp.json()["compatible"] is True


async def test_licensing_flow(client):
    resp = await client.post("/api/v1/licenses", json={"org_ref": "org:api-acme", "license_type": "enterprise", "seats_total": 5})
    assert resp.status_code == 201
    lic = resp.json()

    resp = await client.post(f"/api/v1/licenses/{lic['id']}/assign-seat")
    assert resp.status_code == 200
    assert resp.json()["seats_used"] == 1

    resp = await client.get(f"/api/v1/licenses/{lic['id']}/assert-active")
    assert resp.status_code == 200
    assert resp.json()["active"] is True

    resp = await client.post(f"/api/v1/licenses/{lic['id']}/suspend")
    assert resp.status_code == 200

    resp = await client.get(f"/api/v1/licenses/{lic['id']}/assert-active")
    assert resp.status_code == 400


async def test_environment_flow(client):
    resp = await client.post("/api/v1/environments", json={"name": "api-prod-1", "environment_type": "production"})
    assert resp.status_code == 201
    env = resp.json()

    resp = await client.post(f"/api/v1/environments/{env['id']}/deactivate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


async def test_validation_and_rollback_flow(client):
    resp = await client.post("/api/v1/deployments", json={"release_id": "rel-2", "environment_id": "env-2", "target_type": "on_prem"})
    deployment = resp.json()

    resp = await client.post("/api/v1/health-checks", json={"deployment_id": deployment["id"], "target": "database", "status": "passed"})
    assert resp.status_code == 201

    resp = await client.post(f"/api/v1/health-checks/run-all/{deployment['id']}")
    assert resp.status_code == 200
    assert len(resp.json()) > 0

    resp = await client.get(f"/api/v1/health-checks/by-deployment/{deployment['id']}/is-healthy")
    assert resp.status_code == 200

    resp = await client.post("/api/v1/rollbacks", json={"deployment_id": deployment["id"], "rollback_type": "automatic"})
    assert resp.status_code == 201
    rollback = resp.json()

    resp = await client.post(f"/api/v1/rollbacks/{rollback['id']}/start")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/rollbacks/{rollback['id']}/complete")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"


async def test_security_flow(client):
    resp = await client.post("/api/v1/artifacts", json={
        "release_id": "rel-sec-1", "artifact_type": "helm_chart", "name": "backend-chart", "version": "1.0.0",
    })
    artifact = resp.json()

    resp = await client.post("/api/v1/sboms", json={"artifact_id": artifact["id"], "content_ref": "s3://sboms/1.json"})
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/sboms/by-artifact/{artifact['id']}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    payload_b64 = base64.b64encode(b"chart-bytes").decode()
    resp = await client.post("/api/v1/artifact-signatures", json={
        "artifact_id": artifact["id"], "payload_b64": payload_b64, "secret": "top-secret",
    })
    assert resp.status_code == 201

    resp = await client.post("/api/v1/artifact-signatures/verify", json={
        "artifact_id": artifact["id"], "payload_b64": payload_b64, "secret": "top-secret",
    })
    assert resp.status_code == 200
    assert resp.json()["verified"] is True

    resp = await client.post("/api/v1/release-approvals", json={"release_id": "rel-sec-1", "approver_id": "u1"})
    assert resp.status_code == 201
    approval = resp.json()

    resp = await client.post(f"/api/v1/release-approvals/{approval['id']}/decide", json={"decision": "approved"})
    assert resp.status_code == 200

    resp = await client.get("/api/v1/release-approvals/by-release/rel-sec-1/assert-approved")
    assert resp.status_code == 200
    assert resp.json()["approved"] is True


async def test_analytics_flow(client):
    await client.post("/api/v1/analytics/metrics", json={"metric_type": "deployment_succeeded"})
    await client.post("/api/v1/analytics/metrics", json={"metric_type": "deployment_failed"})
    await client.post("/api/v1/analytics/metrics", json={"metric_type": "deployment_duration_seconds", "value": 42.0})

    resp = await client.get("/api/v1/analytics/deployment-success-rate")
    assert resp.status_code == 200
    assert resp.json()["rate"] == 0.5

    resp = await client.get("/api/v1/analytics/average-deployment-duration")
    assert resp.status_code == 200
    assert resp.json()["average_seconds"] == 42.0

    resp = await client.post("/api/v1/adoption-snapshots", json={"version": "1.0.0", "adoption_pct": 33.3})
    assert resp.status_code == 201

    resp = await client.get("/api/v1/adoption-snapshots/1.0.0")
    assert resp.status_code == 200
    assert resp.json()["adoption_pct"] == 33.3
