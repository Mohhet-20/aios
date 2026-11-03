"""CRUD smoke tests across a representative repository from each
module — proves the schema, base repository, and RepositoryRegistry
wiring all work together before any service layer is built on top."""
from __future__ import annotations

import pytest

from gateway_platform.models.api_management import ApiKeyModel
from gateway_platform.models.events import EventTopicModel
from gateway_platform.models.gateway import ApiRouteModel
from gateway_platform.models.integrations import ConnectorModel
from gateway_platform.models.mesh import ServiceRegistrationModel
from gateway_platform.models.webhooks import WebhookSubscriptionModel

TENANT = "smoke-tenant"


@pytest.mark.asyncio
async def test_api_route_crud(repos):
    route = ApiRouteModel(tenant_id=TENANT, path="/v1/widgets", method="GET", target_service="widgets-svc")
    route = await repos.api_routes.add(route)
    assert route.id
    fetched = await repos.api_routes.get_by_path_method(TENANT, "/v1/widgets", "GET")
    assert fetched is not None and fetched.id == route.id
    listed = await repos.api_routes.list_for_tenant(TENANT)
    assert any(r.id == route.id for r in listed)


@pytest.mark.asyncio
async def test_api_key_crud(repos):
    key = ApiKeyModel(tenant_id=TENANT, name="smoke-key", key_hash="hash123", key_prefix="gwk_abc123")
    key = await repos.api_keys.add(key)
    fetched = await repos.api_keys.get_by_key_hash("hash123")
    assert fetched is not None and fetched.id == key.id


@pytest.mark.asyncio
async def test_service_registration_crud(repos):
    svc = ServiceRegistrationModel(tenant_id=TENANT, name="widgets-svc")
    svc = await repos.services.add(svc)
    fetched = await repos.services.get_by_name(TENANT, "widgets-svc")
    assert fetched is not None and fetched.id == svc.id


@pytest.mark.asyncio
async def test_event_topic_crud(repos):
    topic = EventTopicModel(tenant_id=TENANT, name="widget.created", category="system")
    topic = await repos.event_topics.add(topic)
    fetched = await repos.event_topics.get_by_name(TENANT, "widget.created")
    assert fetched is not None and fetched.id == topic.id


@pytest.mark.asyncio
async def test_connector_crud(repos):
    connector = ConnectorModel(tenant_id=TENANT, connector_type="slack", name="Slack")
    connector = await repos.connectors.add(connector)
    fetched = await repos.connectors.get_by_type(TENANT, "slack")
    assert fetched is not None and fetched.id == connector.id


@pytest.mark.asyncio
async def test_webhook_subscription_crud(repos):
    sub = WebhookSubscriptionModel(
        tenant_id=TENANT, target_url="https://example.com/hook", secret_ref="vault-ref-1", event_types=["route.created"],
    )
    sub = await repos.webhook_subscriptions.add(sub)
    active = await repos.webhook_subscriptions.list_active(TENANT)
    assert any(s.id == sub.id for s in active)
