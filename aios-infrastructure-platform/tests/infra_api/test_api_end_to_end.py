"""Drives the platform purely through HTTP, end to end, across every
domain — the same style as every prior AIOS platform's API test
suite. Uses a dedicated tenant id (`api-e2e-tenant`, set in
conftest.py's `client` fixture) rather than the generic ids used
throughout the unit-level test suites, to keep this suite's state
isolated from those."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
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



@pytest.mark.asyncio
async def test_containers_flow(client):
    resp = await client.post("/api/v1/images", json={"repository": "aios/api-e2e", "tag": "1.0.0"})
    assert resp.status_code == 201
    image = resp.json()
    assert image["status"] == "building"

    resp = await client.post(f"/api/v1/images/{image['id']}/scan/start")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/images/{image['id']}/scan/result", json={"severity": "low", "finding_count": 1})
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/images/{image['id']}/sign", json={"signer": "ci-bot", "signature": "sig-1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "signed"

    resp = await client.post(f"/api/v1/images/{image['id']}/publish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"

    resp = await client.get("/api/v1/images", params={"repository": "aios/api-e2e"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    # critical finding on a fresh image blocks publish with a 422
    resp = await client.post("/api/v1/images", json={"repository": "aios/api-e2e-2", "tag": "1.0.0"})
    image2 = resp.json()
    await client.post(f"/api/v1/images/{image2['id']}/scan/start")
    resp = await client.post(f"/api/v1/images/{image2['id']}/scan/result", json={"severity": "critical", "finding_count": 1})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_kubernetes_flow(client):
    resp = await client.post("/api/v1/k8s/clusters", json={"name": "e2e-cluster", "provider": "aws", "region": "us-east-1"})
    assert resp.status_code == 201
    cluster = resp.json()

    resp = await client.post(f"/api/v1/k8s/clusters/{cluster['id']}/healthy")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"

    resp = await client.post(
        f"/api/v1/k8s/clusters/{cluster['id']}/node-pools",
        json={"name": "cpu-pool", "instance_type": "m5.xlarge", "min_nodes": 1, "max_nodes": 4},
    )
    assert resp.status_code == 201
    pool = resp.json()

    resp = await client.post(f"/api/v1/k8s/node-pools/{pool['id']}/scale", json={"target_nodes": 3})
    assert resp.status_code == 200
    assert resp.json()["current_nodes"] == 3

    resp = await client.post(f"/api/v1/k8s/clusters/{cluster['id']}/namespaces", json={"name": "e2e-ns"})
    assert resp.status_code == 201

    resp = await client.post(
        f"/api/v1/k8s/clusters/{cluster['id']}/resources",
        json={"namespace": "e2e-ns", "kind": "deployment", "name": "api", "replicas": 2},
    )
    assert resp.status_code == 200
    resource = resp.json()
    assert resource["replicas"] == 2

    resp = await client.get(f"/api/v1/k8s/clusters/{cluster['id']}/resources", params={"namespace": "e2e-ns"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get("/api/v1/k8s/clusters/no-such-cluster/node-pools")
    assert resp.status_code == 200  # empty list, not an error — listing doesn't require existence
    resp = await client.post("/api/v1/k8s/clusters/no-such-cluster/node-pools", json={"name": "x", "instance_type": "t3.micro"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cicd_flow(client):
    resp = await client.post("/api/v1/cicd/pipelines", json={"name": "e2e-pipeline", "repository": "org/e2e", "stages": ["build", "test", "deploy"]})
    assert resp.status_code == 201
    pipeline = resp.json()

    resp = await client.post(f"/api/v1/cicd/pipelines/{pipeline['id']}/runs", json={"commit_sha": "abc123"})
    assert resp.status_code == 201
    run = resp.json()

    resp = await client.post(f"/api/v1/cicd/runs/{run['id']}/start")
    assert resp.status_code == 200

    for stage in ["build", "test", "deploy"]:
        resp = await client.post(f"/api/v1/cicd/runs/{run['id']}/stages/{stage}/start")
        assert resp.status_code == 200
        resp = await client.post(f"/api/v1/cicd/runs/{run['id']}/stages/{stage}/complete", json={"success": True})
        assert resp.status_code == 200

    resp = await client.post(f"/api/v1/cicd/runs/{run['id']}/gates", json={"name": "prod-gate", "required_approvals": 1})
    assert resp.status_code == 201
    gate = resp.json()
    resp = await client.post(f"/api/v1/cicd/gates/{gate['id']}/approve")
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    resp = await client.post("/api/v1/cicd/releases", json={"name": "e2e-release", "version": "1.0.0"})
    assert resp.status_code == 201
    release = resp.json()
    resp = await client.post(f"/api/v1/cicd/releases/{release['id']}/submit")
    assert resp.status_code == 200
    resp = await client.post(f"/api/v1/cicd/releases/{release['id']}/approve")
    assert resp.status_code == 200
    resp = await client.post(f"/api/v1/cicd/releases/{release['id']}/publish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "released"


@pytest.mark.asyncio
async def test_model_registry_flow(client):
    resp = await client.post("/api/v1/models", json={"name": "e2e-model"})
    assert resp.status_code == 201
    model = resp.json()

    resp = await client.post(f"/api/v1/models/{model['id']}/versions", json={"metrics": {"auc": 0.9}})
    assert resp.status_code == 201
    version = resp.json()
    assert version["stage"] == "development"

    resp = await client.post(f"/api/v1/models/versions/{version['id']}/promote", json={"requested_stage": "staging"})
    assert resp.status_code == 201
    approval = resp.json()
    assert approval["status"] == "pending"

    resp = await client.post(f"/api/v1/models/approvals/{approval['id']}/decide", json={"approved": True})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    resp = await client.get(f"/api/v1/models/{model['id']}/versions")
    assert resp.status_code == 200
    assert resp.json()[0]["stage"] == "staging"


@pytest.mark.asyncio
async def test_experiments_flow(client):
    resp = await client.post("/api/v1/experiments", json={"name": "e2e-experiment"})
    assert resp.status_code == 201
    experiment = resp.json()

    resp = await client.post(f"/api/v1/experiments/{experiment['id']}/runs", json={"run_name": "trial-1"})
    assert resp.status_code == 201
    run = resp.json()

    resp = await client.post(f"/api/v1/experiments/runs/{run['id']}/metrics", json={"key": "loss", "value": 0.5, "step": 0})
    assert resp.status_code == 201

    resp = await client.post(f"/api/v1/experiments/runs/{run['id']}/complete")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    resp = await client.get(f"/api/v1/experiments/runs/{run['id']}/metrics")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_feature_store_flow(client):
    resp = await client.post("/api/v1/features/groups", json={"name": "e2e-features", "entity_key": "user_id", "online_enabled": True})
    assert resp.status_code == 201
    group = resp.json()

    resp = await client.post(f"/api/v1/features/groups/{group['id']}/features", json={"name": "risk_score", "value_type": "float"})
    assert resp.status_code == 201
    feature = resp.json()

    resp = await client.post(f"/api/v1/features/{feature['id']}/publish")
    assert resp.status_code == 422  # online group requires a validation rule first

    resp = await client.post(f"/api/v1/features/{feature['id']}/rules", json={"rule_type": "range", "config": {"min": 0, "max": 1}})
    assert resp.status_code == 201

    resp = await client.post(f"/api/v1/features/{feature['id']}/publish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


@pytest.mark.asyncio
async def test_artifacts_flow(client):
    resp = await client.post("/api/v1/artifacts", json={"name": "e2e-artifact", "artifact_type": "model"})
    assert resp.status_code == 201
    artifact = resp.json()

    resp = await client.post(f"/api/v1/artifacts/{artifact['id']}/versions", json={"storage_uri": "s3://bucket/e2e.bin", "checksum": "abc"})
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/artifacts/{artifact['id']}/versions/latest")
    assert resp.status_code == 200
    version = resp.json()

    resp = await client.post(f"/api/v1/artifacts/versions/{version['id']}/verify", json={"expected_checksum": "abc"})
    assert resp.status_code == 200
    assert resp.json()["verified"] is True

    resp = await client.post(f"/api/v1/artifacts/versions/{version['id']}/verify", json={"expected_checksum": "tampered"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_inference_flow(client):
    resp = await client.post("/api/v1/inference/services", json={"name": "e2e-inf-service"})
    assert resp.status_code == 201
    service = resp.json()

    resp = await client.post(f"/api/v1/inference/services/{service['id']}/running")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/inference/services/{service['id']}/routes", json={"path": "/v1/stable", "weight": 100})
    assert resp.status_code == 201
    route = resp.json()

    resp = await client.put(f"/api/v1/inference/services/{service['id']}/routes/weights", json={"weights": {route["id"]: 100}})
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/inference/services/{service['id']}/scale", json={"replicas": 5})
    assert resp.status_code == 200
    assert resp.json()["replicas"] == 5


@pytest.mark.asyncio
async def test_deployment_flow(client):
    resp = await client.post("/api/v1/deployments", json={"name": "e2e-deploy", "target_version": "1.0.0", "strategy": "canary"})
    assert resp.status_code == 201
    deployment = resp.json()

    resp = await client.post(f"/api/v1/deployments/{deployment['id']}/start")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/deployments/{deployment['id']}/canary/advance", json={"step_percentage": 25})
    assert resp.status_code == 200
    assert resp.json()["traffic_percentage"] == 25

    resp = await client.post(f"/api/v1/deployments/{deployment['id']}/succeed")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/deployments/{deployment['id']}/rollback", json={"reason": "post-hoc revert"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "rolled_back"

    resp = await client.post("/api/v1/deployments/feature-flags", json={"key": "e2e-flag", "rollout_percentage": 50})
    assert resp.status_code == 201
    resp = await client.post("/api/v1/deployments/feature-flags/e2e-flag/enable")
    assert resp.status_code == 200
    assert resp.json()["is_enabled"] is True


@pytest.mark.asyncio
async def test_autoscaling_flow(client):
    resp = await client.post(
        "/api/v1/autoscaling/policies",
        json={"resource_type": "node_pool", "resource_id": "e2e-pool", "policy_type": "horizontal", "min_capacity": 1, "max_capacity": 10},
    )
    assert resp.status_code == 201
    policy = resp.json()

    resp = await client.post(f"/api/v1/autoscaling/policies/{policy['id']}/evaluate", json={"current_capacity": 2, "desired_capacity": 5})
    assert resp.status_code == 200
    assert resp.json()["to_capacity"] == 5


@pytest.mark.asyncio
async def test_cloud_flow(client):
    resp = await client.post("/api/v1/cloud/accounts", json={"provider": "aws", "account_ref": "e2e-acct", "display_name": "E2E AWS"})
    assert resp.status_code == 201
    account = resp.json()

    resp = await client.post(f"/api/v1/cloud/accounts/{account['id']}/resources", json={"region": "us-east-1", "resource_type": "vm", "external_id": "vm-e2e"})
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/cloud/accounts/{account['id']}/resources")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_recovery_flow(client):
    resp = await client.post("/api/v1/recovery/backups", json={"resource_type": "cluster", "resource_id": "e2e-cluster"})
    assert resp.status_code == 201
    backup = resp.json()
    await client.post(f"/api/v1/recovery/backups/{backup['id']}/start")
    resp = await client.post(f"/api/v1/recovery/backups/{backup['id']}/complete", json={"size_bytes": 100})
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    resp = await client.post("/api/v1/recovery/plans", json={"name": "e2e-plan", "resource_type": "cluster"})
    assert resp.status_code == 201
    plan = resp.json()

    resp = await client.post(f"/api/v1/recovery/plans/{plan['id']}/executions", json={})
    assert resp.status_code == 201
    execution = resp.json()
    resp = await client.post(f"/api/v1/recovery/executions/{execution['id']}/start")
    assert resp.status_code == 200
    resp = await client.post(f"/api/v1/recovery/executions/{execution['id']}/complete")
    assert resp.status_code == 200

    resp = await client.post("/api/v1/recovery/failovers", json={"cluster_id": "e2e-cluster", "from_region": "us-east-1", "to_region": "us-west-2"})
    assert resp.status_code == 201
    event = resp.json()
    resp = await client.post(f"/api/v1/recovery/failovers/{event['id']}/complete")
    assert resp.status_code == 409  # cannot complete directly from "initiated"
    resp = await client.post(f"/api/v1/recovery/failovers/{event['id']}/in-progress")
    assert resp.status_code == 200
    resp = await client.post(f"/api/v1/recovery/failovers/{event['id']}/complete")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_observability_flow(client):
    resp = await client.post("/api/v1/observability/metrics", json={"metric_name": "e2e_cpu", "value": 42.0})
    assert resp.status_code == 201

    resp = await client.get("/api/v1/observability/metrics", params={"metric_name": "e2e_cpu"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get("/api/v1/observability/deployments/success-rate")
    assert resp.status_code == 200
    assert "rate" in resp.json()

    resp = await client.post("/api/v1/observability/clusters/e2e-cluster/health-checks", json={"status": "healthy"})
    assert resp.status_code == 201


@pytest.mark.asyncio
async def test_security_flow(client):
    resp = await client.post("/api/v1/infra-security/network-policies", json={"name": "e2e-deny", "rules": {"deny_destinations": ["10.0.0.99"]}})
    assert resp.status_code == 201

    resp = await client.post("/api/v1/infra-security/network-policies/evaluate", json={"destination": "10.0.0.99"})
    assert resp.status_code == 403

    resp = await client.post(
        "/api/v1/infra-security/runtime-policies", json={"name": "e2e-cpu-cap", "policy_type": "resource_limit", "rules": {"max_cpu": 2}}
    )
    assert resp.status_code == 201

    resp = await client.post("/api/v1/infra-security/runtime-policies/evaluate", json={"context": {"cpu_requested": 8}})
    assert resp.status_code == 403

    resp = await client.post("/api/v1/infra-security/roles/grant", json={"principal_id": "e2e-user", "role": "operator"})
    assert resp.status_code == 201

    resp = await client.get("/api/v1/infra-security/roles/e2e-user")
    assert resp.status_code == 200
    assert resp.json()[0]["role"] == "operator"
