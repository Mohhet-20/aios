"""Drives the platform purely through HTTP, end to end, across every
domain — the same style as every prior AIOS platform's API test
suite. Uses a dedicated tenant id (`api-e2e-tenant`, set in
conftest.py's `client` fixture) rather than the generic ids used
throughout the unit-level test suites, to keep this suite's state
isolated from those."""
from __future__ import annotations

import pytest

from developer_platform.dependencies.dependencies import get_webhook_delivery_service
from developer_platform.webhook_platform.delivery_service import WebhookDeliveryService


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
async def test_api_platform_flow(client):
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
    assert len(resp.json()) >= 1

    resp = await client.post("/api/v1/api-usage/record", json={"api_key_id": key_id, "endpoint": "/x", "method": "GET", "status_code": 200})
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/api-keys/{key_id}/rotate")
    assert resp.status_code == 200
    new_raw_key = resp.json()["raw_key"]
    assert new_raw_key != raw_key

    resp = await client.post("/api/v1/api-versions", json={"version": "2026-01-01", "notes": "e2e"})
    assert resp.status_code == 201
    resp = await client.get("/api/v1/api-versions")
    assert resp.status_code == 200
    resp = await client.post("/api/v1/api-versions/2026-01-01/deprecate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deprecated"


@pytest.mark.asyncio
async def test_sdk_platform_flow(client):
    resp = await client.post(
        "/api/v1/sdk/compatibility",
        json={"language": "python", "sdk_major_version": 1, "min_api_version": "2025-01-01", "is_supported": True},
    )
    assert resp.status_code == 201

    resp = await client.post(
        "/api/v1/sdk/compatibility/check",
        json={"language": "python", "sdk_major_version": 1, "api_version": "2025-06-01"},
    )
    assert resp.status_code == 200
    assert resp.json()["compatible"] is True

    resp = await client.post(
        "/api/v1/sdk/packages", json={"language": "python", "version": "1.0.0", "storage_uri": "s3://x/y"},
    )
    assert resp.status_code == 201

    resp = await client.get("/api/v1/sdk/packages/python")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_cli_platform_flow(client):
    resp = await client.post("/api/v1/cli/sessions", json={"developer_id": "dev-1"})
    assert resp.status_code == 201
    body = resp.json()
    assert body["cli_token"]
    cli_token = body["cli_token"]
    session_id = body["session"]["id"]

    resp = await client.post("/api/v1/cli/sessions/verify", json={"cli_token": cli_token})
    assert resp.status_code == 200

    resp = await client.post("/api/v1/cli/commands", json={"session_id": session_id, "command": "aios deploy", "exit_code": 0})
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/cli/commands/for-session/{session_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.post(f"/api/v1/cli/sessions/{session_id}/revoke")
    assert resp.status_code == 200
    assert resp.json()["status"] == "revoked"


@pytest.mark.asyncio
async def test_plugin_sdk_flow(client):
    resp = await client.post("/api/v1/plugins", json={"name": "e2e-plugin", "category": "tool"})
    assert resp.status_code == 201
    plugin_id = resp.json()["id"]

    manifest = {
        "name": "e2e-plugin", "version": "1.0.0", "entrypoint": "main.py", "category": "tool", "permissions": ["network.outbound"],
    }
    resp = await client.post(f"/api/v1/plugins/{plugin_id}/versions", json={"version": "1.0.0", "manifest": manifest})
    assert resp.status_code == 201
    version_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/plugins/versions/{version_id}/validate")
    assert resp.status_code == 200
    assert resp.json()["validation_errors"] == []

    resp = await client.post(f"/api/v1/plugins/versions/{version_id}/sign", json={"signed_by": "ci-bot"})
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/plugins/versions/{version_id}/publish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"

    resp = await client.post(
        f"/api/v1/plugins/versions/{version_id}/package", json={"files": {"main.py": "print('hi')"}, "storage_uri": "s3://pkg"},
    )
    assert resp.status_code == 200

    resp = await client.post(f"/api/v1/plugins/marketplace/{plugin_id}/submit")
    assert resp.status_code == 200
    resp = await client.post(f"/api/v1/plugins/marketplace/{plugin_id}/approve", json={"reviewer_id": "rev-1"})
    assert resp.status_code == 200
    assert resp.json()["review_status"] == "approved"

    resp = await client.post(f"/api/v1/plugins/marketplace/{plugin_id}/install")
    assert resp.status_code == 200
    resp = await client.post(f"/api/v1/plugins/marketplace/{plugin_id}/rate", json={"rating_avg": 4.5})
    assert resp.status_code == 200

    resp = await client.get("/api/v1/plugins/marketplace")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_extension_framework_flow(client):
    resp = await client.post("/api/v1/extension-points", json={"category": "tool", "name": "e2e-point"})
    assert resp.status_code == 201
    point_id = resp.json()["id"]

    resp = await client.get("/api/v1/extension-points")
    assert resp.status_code == 200
    resp = await client.get("/api/v1/extension-points/tool")
    assert resp.status_code == 200

    resp = await client.post("/api/v1/extension-registrations", json={"extension_point_id": point_id, "name": "e2e-reg"})
    assert resp.status_code == 201
    reg_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/extension-registrations/{reg_id}/activate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"

    resp = await client.get(f"/api/v1/extension-registrations/for-point/{point_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


@pytest.mark.asyncio
async def test_webhook_platform_flow(client, app, repos):
    """`attempt_delivery` defaults to a real outbound HTTP POST
    (`default_sender`) — this test injects a fake service instance
    whose `attempt_delivery` always uses a stub sender, so the e2e
    suite never makes a live network call."""

    def _stub_sender(url, payload, signature):
        return True, None

    class _StubbedDeliveryService(WebhookDeliveryService):
        async def attempt_delivery(self, tenant_id, delivery_id, *, secret, sender=None):
            return await super().attempt_delivery(tenant_id, delivery_id, secret=secret, sender=_stub_sender)

    app.dependency_overrides[get_webhook_delivery_service] = lambda: _StubbedDeliveryService(repos)

    resp = await client.post(
        "/api/v1/webhooks/subscriptions", json={"target_url": "https://example.com/hook", "event_types": ["plugin.published"]},
    )
    assert resp.status_code == 201
    body = resp.json()
    subscription_id = body["subscription"]["id"]
    raw_secret = body["raw_secret"]
    assert raw_secret

    resp = await client.post("/api/v1/webhooks/deliveries/dispatch", json={"event_type": "plugin.published", "payload": {"x": 1}})
    assert resp.status_code == 201
    deliveries = resp.json()
    assert len(deliveries) == 1
    delivery_id = deliveries[0]["id"]

    resp = await client.post(f"/api/v1/webhooks/deliveries/{delivery_id}/attempt", json={"secret": raw_secret})
    assert resp.status_code == 200

    resp = await client.get(f"/api/v1/webhooks/deliveries/for-subscription/{subscription_id}")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.post(f"/api/v1/webhooks/subscriptions/{subscription_id}/deactivate")
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_mcp_integration_flow(client):
    resp = await client.post(
        "/api/v1/mcp/servers", json={"name": "e2e-server", "transport": "stdio", "endpoint_ref": "stdio://local"},
    )
    assert resp.status_code == 201
    server_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/mcp/servers/{server_id}/connect")
    assert resp.status_code == 200
    assert resp.json()["status"] == "connected"

    resp = await client.post(
        f"/api/v1/mcp/servers/{server_id}/discover",
        json={"resources": [{"uri": "file:///a.txt", "name": "a"}], "tools": [{"name": "search"}], "prompts": [{"name": "greet"}]},
    )
    assert resp.status_code == 200
    assert len(resp.json()["tools"]) == 1

    resp = await client.post("/api/v1/mcp/sessions", json={"mcp_server_id": server_id, "client_id": "c1", "permissions": ["tools.invoke"]})
    assert resp.status_code == 201
    session_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/mcp/sessions/{session_id}/check-permission", json={"required": "tools.invoke"})
    assert resp.status_code == 200
    assert resp.json()["allowed"] is True

    resp = await client.post(f"/api/v1/mcp/sessions/{session_id}/close")
    assert resp.status_code == 200
    assert resp.json()["status"] == "closed"


@pytest.mark.asyncio
async def test_codegen_flow(client):
    resp = await client.post("/api/v1/codegen/jobs", json={"target": "python", "source_spec_ref": "openapi://e2e"})
    assert resp.status_code == 201
    job_id = resp.json()["id"]

    spec = {
        "info": {"title": "E2E API"},
        "paths": {
            "/widgets": {"get": {"operationId": "list_widgets", "responses": {"200": {}}}},
        },
    }
    resp = await client.post(f"/api/v1/codegen/jobs/{job_id}/run", json={"spec": spec})
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    resp = await client.get(f"/api/v1/codegen/jobs/{job_id}/artifacts")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    resp = await client.get("/api/v1/codegen/jobs")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_developer_portal_flow(client):
    resp = await client.post(
        "/api/v1/portal/content", json={"content_type": "doc", "slug": "e2e-doc", "title": "E2E Doc", "body": "hello"},
    )
    assert resp.status_code == 201
    content_id = resp.json()["id"]

    resp = await client.patch(f"/api/v1/portal/content/{content_id}", json={"body": "hello v2"})
    assert resp.status_code == 200
    assert resp.json()["version"] == 2

    resp = await client.post(f"/api/v1/portal/content/{content_id}/publish")
    assert resp.status_code == 200
    assert resp.json()["status"] == "published"

    resp = await client.get("/api/v1/portal/content/doc/e2e-doc")
    assert resp.status_code == 200

    resp = await client.get("/api/v1/portal/content/doc")
    assert resp.status_code == 200

    resp = await client.get("/api/v1/portal/content")
    assert resp.status_code == 200

    resp = await client.post("/api/v1/portal/sandboxes", json={"developer_id": "dev-e2e"})
    assert resp.status_code == 201
    sandbox_id = resp.json()["id"]

    resp = await client.post(f"/api/v1/portal/sandboxes/{sandbox_id}/mark-running")
    assert resp.status_code == 200
    assert resp.json()["status"] == "running"

    resp = await client.get("/api/v1/portal/sandboxes/for-developer/dev-e2e")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.post(f"/api/v1/portal/sandboxes/{sandbox_id}/terminate")
    assert resp.status_code == 200
    assert resp.json()["status"] == "terminated"


@pytest.mark.asyncio
async def test_registry_platform_flow(client):
    resp = await client.post("/api/v1/registry/packages", json={"name": "e2e-pkg", "package_type": "sdk"})
    assert resp.status_code == 201
    package_id = resp.json()["id"]

    resp = await client.post(
        f"/api/v1/registry/packages/{package_id}/versions",
        json={"version": "1.0.0", "language": "python", "storage_uri": "s3://pkg/1.0.0"},
    )
    assert resp.status_code == 201

    resp = await client.get(f"/api/v1/registry/packages/{package_id}/versions")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.get("/api/v1/registry/packages/by-type/sdk")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    resp = await client.post("/api/v1/registry/packages", json={"name": "e2e-pkg-dep", "package_type": "sdk"})
    assert resp.status_code == 201
    dep_package_id = resp.json()["id"]
    resp = await client.post(
        f"/api/v1/registry/packages/{dep_package_id}/versions",
        json={"version": "1.0.0", "language": "python", "storage_uri": "s3://pkg-dep/1.0.0"},
    )
    assert resp.status_code == 201

    resp = await client.post(
        f"/api/v1/registry/packages/{package_id}/dependencies",
        json={"version": "1.0.0", "depends_on_name": "e2e-pkg-dep", "depends_on_type": "sdk", "constraint": ">=1.0"},
    )
    assert resp.status_code == 200

    resp = await client.get(f"/api/v1/registry/packages/{package_id}/dependencies/resolve", params={"version": "1.0.0"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = await client.post(f"/api/v1/registry/packages/{package_id}/deprecate", json={"version": "1.0.0"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "deprecated"
    assert "recommended_removal_at" in body


@pytest.mark.asyncio
async def test_developer_analytics_flow(client):
    resp = await client.post(
        "/api/v1/analytics/usage-events",
        json={"event_type": "sdk_call", "resource_type": "sdk", "resource_id": "python-sdk", "developer_id": "dev-a"},
    )
    assert resp.status_code in (201, 204)

    resp = await client.get("/api/v1/analytics/usage-events/summary")
    assert resp.status_code == 200

    resp = await client.get("/api/v1/analytics/usage-events")
    assert resp.status_code == 200

    resp = await client.get("/api/v1/analytics/dashboard/summary")
    assert resp.status_code == 200

    resp = await client.get("/api/v1/analytics/dashboard/top-resources")
    assert resp.status_code == 200

    resp = await client.get("/api/v1/analytics/dashboard/most-active-developers")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_dev_security_flow(client):
    resp = await client.post("/api/v1/security/rbac/grant", json={"principal_id": "dev-sec-1", "role": "admin"})
    assert resp.status_code == 201

    resp = await client.get("/api/v1/security/rbac/for-principal/dev-sec-1")
    assert resp.status_code == 200
    assert resp.json()[0]["role"] == "admin"

    resp = await client.post("/api/v1/security/secrets", json={"name": "e2e-secret", "reference_type": "webhook_secret"})
    assert resp.status_code == 201
    reference_id = resp.json()["id"]
    assert resp.json()["material_ref"].startswith("vault://")

    resp = await client.post(f"/api/v1/security/secrets/{reference_id}/rotate")
    assert resp.status_code == 200

    resp = await client.get("/api/v1/security/secrets/by-type/webhook_secret")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1

    resp = await client.post(
        "/api/v1/security/plugin-isolation/evaluate",
        json={"manifest_permissions": ["network.outbound"], "denied_permissions": ["filesystem.write"]},
    )
    assert resp.status_code == 200
    assert resp.json()["allowed"] is True

    resp = await client.post(
        "/api/v1/security/oauth/validate-scopes", json={"requested": ["read"], "granted": ["read", "write"]},
    )
    assert resp.status_code == 200
    assert resp.json()["valid"] is True

    resp = await client.post(
        "/api/v1/security/oauth/narrow-scopes", json={"requested": ["read", "write"], "granted": ["read"]},
    )
    assert resp.status_code == 200
    assert resp.json()["scopes"] == ["read"]


@pytest.mark.asyncio
async def test_error_paths_map_to_expected_status_codes(client):
    resp = await client.post("/api/v1/api-keys/verify", json={"raw_key": "dpk_does-not-exist"})
    assert resp.status_code == 401  # unknown key rejected the same way an invalid key would be, not leaking existence

    resp = await client.post("/api/v1/mcp/sessions/no-such-session/close")
    assert resp.status_code == 404

    resp = await client.get("/api/v1/portal/content/doc/no-such-slug")
    assert resp.status_code == 404

    resp = await client.post(
        "/api/v1/security/plugin-isolation/evaluate",
        json={"manifest_permissions": ["secrets.read"], "allowed_permissions": ["network.outbound"]},
    )
    assert resp.status_code == 200
    assert resp.json()["allowed"] is False
