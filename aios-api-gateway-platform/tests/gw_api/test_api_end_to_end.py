"""Drives the platform purely through HTTP, end to end, across every
domain — the same style as every other AIOS platform's API test
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
async def test_gateway_core_flow(client):
    resp = await client.post(
        "/api/v1/routes",
        json={"path": "/orders", "method": "GET", "protocol": "rest", "visibility": "external", "target_service": "orders-svc"},
    )
    assert resp.status_code == 201
    route = resp.json()
    route_id = route["id"]
    assert route["status"] == "draft"

    resp = await client.post(f"/api/v1/routes/{route_id}/activate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    resp = await client.get("/api/v1/routes/match", params={"path": "/orders", "method": "GET"})
    assert resp.status_code == 200
    assert resp.json()["id"] == route_id

    resp = await client.get("/api/v1/routes")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    resp = await client.post("/api/v1/routes", json={"path": "/orders", "method": "GET", "target_service": "orders-svc"})
    assert resp.status_code == 409  # RouteAlreadyExistsError

    return route_id


@pytest.mark.asyncio
async def test_api_management_flow(client):
    resp = await client.post("/api/v1/api-keys", json={"name": "e2e-key", "scopes": ["read"], "rate_limit_per_minute": 60})
    assert resp.status_code == 201
    body = resp.json()
    raw_key = body["raw_key"]
    key_id = body["api_key"]["id"]

    resp = await client.post("/api/v1/api-keys/verify", json={"raw_key": raw_key})
    assert resp.status_code == 200
    assert resp.json()["id"] == key_id

    resp = await client.get("/api/v1/api-keys")
    assert resp.status_code == 200

    resp = await client.post("/api/v1/api-usage/record", json={"api_key_id": key_id, "endpoint": "/x", "method": "GET", "status_code": 200})
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/api-keys/{key_id}/rotate")
    assert resp.status_code == 200
    assert resp.json()["raw_key"] != raw_key

    resp = await client.post("/api/v1/api-versions", json={"version": "2026-e2e-01", "notes": "e2e"})
    assert resp.status_code == 201
    resp = await client.get("/api/v1/api-versions")
    assert resp.status_code == 200
    resp = await client.post("/api/v1/api-versions/2026-e2e-01/deprecate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deprecated"

    resp = await client.post("/api/v1/jwt/issue", json={"subject": "user-1", "scopes": ["read"]})
    assert resp.status_code == 200
    token = resp.json()["token"]
    resp = await client.post("/api/v1/jwt/validate", json={"token": token})
    assert resp.status_code == 200
    assert resp.json()["sub"] == "user-1"

    resp = await client.post("/api/v1/oauth-clients", json={"name": "e2e-client"})
    assert resp.status_code == 201
    client_id = resp.json()["client"]["client_id"]
    resp = await client.post(f"/api/v1/oauth-clients/{client_id}/revoke")
    assert resp.status_code == 200
    assert resp.json()["status"] == "revoked"

    route_resp = await client.post("/api/v1/routes", json={"path": "/schema-route", "method": "POST", "target_service": "x"})
    route_id = route_resp.json()["id"]
    resp = await client.post(
        "/api/v1/api-schemas",
        json={"route_id": route_id, "schema_kind": "request", "json_schema": {"type": "object", "required": ["name"]}},
    )
    assert resp.status_code == 201
    resp = await client.post(
        "/api/v1/api-schemas/validate", json={"route_id": route_id, "schema_kind": "request", "payload": {"name": "x"}},
    )
    assert resp.status_code == 200
    resp = await client.post(
        "/api/v1/api-schemas/validate", json={"route_id": route_id, "schema_kind": "request", "payload": {}},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_service_mesh_flow(client):
    resp = await client.post("/api/v1/mesh/services", json={"name": "orders-service"})
    assert resp.status_code == 201
    service_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/mesh/services/{service_id}/instances", json={"host": "10.0.0.1", "port": 8080})
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/mesh/services/{service_id}/instances")
    assert resp.status_code == 200
    instance_id = resp.json()[0]["id"]

    resp = await client.post(f"/api/v1/mesh/load-balancer/{service_id}/configure", json={"strategy": "round_robin"})
    assert resp.status_code == 200

    resp = await client.get(f"/api/v1/mesh/load-balancer/{service_id}/select")
    assert resp.status_code == 200
    assert resp.json()["id"] == instance_id

    resp = await client.get(f"/api/v1/mesh/circuit-breakers/{service_id}")
    assert resp.status_code == 200
    assert resp.json()["state"] == "closed"

    resp = await client.post(f"/api/v1/mesh/circuit-breakers/{service_id}/record-failure")
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/mesh/health-checks/{instance_id}", json={"healthy": True, "latency_ms": 12.5})
    assert resp.status_code == 200
    resp = await client.get(f"/api/v1/mesh/health-checks/{instance_id}")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_traffic_management_flow(client):
    route_resp = await client.post("/api/v1/routes", json={"path": "/traffic-route", "method": "GET", "target_service": "x"})
    route_id = route_resp.json()["id"]

    resp = await client.post(
        "/api/v1/traffic-rules",
        json={"route_id": route_id, "rule_type": "weighted", "config": {"weights": {"a": 1}}, "priority": 10},
    )
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/traffic-rules/for-route/{route_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.post("/api/v1/traffic-rules/resolve", json={"route_id": route_id, "context": {}})
    assert resp.status_code == 200
    assert resp.json()["destination"] == "a"


@pytest.mark.asyncio
async def test_event_platform_flow(client):
    resp = await client.post("/api/v1/events/topics", json={"name": "orders.events", "category": "workflow"})
    assert resp.status_code == 201
    topic_id = resp.json()["id"]

    resp = await client.post("/api/v1/events/subscriptions", json={"topic_id": topic_id, "subscriber": "worker-1"})
    assert resp.status_code == 201

    resp = await client.post("/api/v1/events/messages/publish", json={"topic_id": topic_id, "payload": {"order_id": "o1"}})
    assert resp.status_code == 201
    message_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/events/messages/{message_id}/attempt-delivery")
    assert resp.status_code == 200
    assert resp.json()["status"] == "delivered"

    resp = await client.get(f"/api/v1/events/messages/for-topic/{topic_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_integration_hub_flow(client):
    resp = await client.post("/api/v1/integrations/connectors", json={"connector_type": "slack", "name": "Slack"})
    assert resp.status_code == 201
    connector_id = resp.json()["id"]

    resp = await client.post(
        "/api/v1/integrations/connections", json={"connector_id": connector_id, "name": "Team Slack"},
    )
    assert resp.status_code == 201
    connection_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/integrations/connections/{connection_id}/mark-connected")
    assert resp.status_code == 200
    assert resp.json()["status"] == "connected"


@pytest.mark.asyncio
async def test_webhook_platform_flow(client):
    resp = await client.post(
        "/api/v1/webhooks/subscriptions", json={"target_url": "https://example.com/hook", "event_types": ["order.created"]},
    )
    assert resp.status_code == 201
    body = resp.json()
    subscription_id = body["subscription"]["id"]
    raw_secret = body["raw_secret"]

    resp = await client.post(
        "/api/v1/webhooks/deliveries/dispatch", json={"event_type": "order.created", "payload": {"id": 1}},
    )
    assert resp.status_code == 201
    deliveries = resp.json()
    assert len(deliveries) == 1
    delivery_id = deliveries[0]["id"]

    resp = await client.post(f"/api/v1/webhooks/deliveries/{delivery_id}/attempt", json={"secret": raw_secret})
    assert resp.status_code in (200, 422)  # network call may fail in sandbox; either is a valid outcome

    resp = await client.get(f"/api/v1/webhooks/deliveries/for-subscription/{subscription_id}")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_protocol_translation_flow(client):
    route_resp = await client.post("/api/v1/routes", json={"path": "/proto-route", "method": "POST", "target_service": "x"})
    route_id = route_resp.json()["id"]

    resp = await client.post(
        "/api/v1/protocol-translations",
        json={"route_id": route_id, "translation_pair": "rest_graphql", "config": {"operation_name": "GetX", "field_map": {"a": "b"}}},
    )
    assert resp.status_code == 201

    resp = await client.post(
        "/api/v1/protocol-translations/translate-request",
        json={"route_id": route_id, "translation_pair": "rest_graphql", "payload": {"a": 1}},
    )
    assert resp.status_code == 200
    assert resp.json()["variables"] == {"b": 1}


@pytest.mark.asyncio
async def test_gateway_security_flow(client):
    resp = await client.post("/api/v1/security/policies", json={"name": "e2e-ip-policy", "policy_type": "ip_filter"})
    assert resp.status_code == 201
    policy_id = resp.json()["id"]

    resp = await client.post("/api/v1/security/ip-rules", json={"policy_id": policy_id, "cidr": "10.0.0.0/8", "action": "deny"})
    assert resp.status_code == 201

    resp = await client.post("/api/v1/security/ip-rules/evaluate", json={"policy_id": policy_id, "ip_address": "10.1.1.1"})
    assert resp.status_code == 403

    resp = await client.post("/api/v1/security/threat-detection/scan", json={"text": "<script>bad()</script>"})
    assert resp.status_code == 200
    assert resp.json()["matches"]

    resp = await client.post("/api/v1/security/events", json={"event_type": "ip_blocked", "severity": "high"})
    assert resp.status_code == 201
    resp = await client.get("/api/v1/security/events")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_observability_flow(client):
    resp = await client.post("/api/v1/observability/metrics", json={"metric_type": "latency", "value": 100.0})
    assert resp.status_code == 201

    resp = await client.get("/api/v1/observability/metrics", params={"metric_type": "latency"})
    assert resp.status_code == 200

    resp = await client.post(
        "/api/v1/observability/topology", json={"from_service": "gw", "to_service": "orders", "latency_ms": 20.0},
    )
    assert resp.status_code == 201

    resp = await client.post(
        "/api/v1/observability/analytics",
        json={
            "snapshot_type": "api_usage", "period_start": "2026-01-01T00:00:00Z", "period_end": "2026-01-02T00:00:00Z",
            "data": {"calls": 10},
        },
    )
    assert resp.status_code == 201
    resp = await client.get("/api/v1/observability/analytics/api_usage/latest")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_devx_flow(client):
    route_resp = await client.post("/api/v1/routes", json={"path": "/devx-route", "method": "GET", "target_service": "x"})
    route_id = route_resp.json()["id"]
    await client.post(f"/api/v1/routes/{route_id}/activate")

    resp = await client.get("/api/v1/devx/openapi/spec.json")
    assert resp.status_code == 200
    assert "/devx-route" in resp.json()["paths"]

    resp = await client.post("/api/v1/devx/samples", json={"json_schema": {"type": "object", "properties": {"a": {"type": "string"}}}})
    assert resp.status_code == 200

    resp = await client.post("/api/v1/devx/sdk-jobs", json={"language": "python", "api_version": "v1"})
    assert resp.status_code == 201
    job_id = resp.json()["id"]
    resp = await client.post(f"/api/v1/devx/sdk-jobs/{job_id}/run", json={"spec": {"paths": {"/devx-route": {"get": {}}}}})
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    resp = await client.post(
        "/api/v1/devx/test-console/execute", json={"route_id": route_id, "request_payload": {"a": 1}},
    )
    assert resp.status_code == 201
    assert resp.json()["status_code"] == 200
