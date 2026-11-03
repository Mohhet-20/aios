import httpx
import pytest

from workflow_platform.core.exceptions import ValidationError
from workflow_platform.domain.enums import WebhookDeliveryStatus
from workflow_platform.events.event_bus import EventBus
from workflow_platform.events.subscription_service import SubscriptionService
from workflow_platform.models.workspace import WorkspaceModel


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Events Co", organization_id="org-1", slug="events-co"))


@pytest.mark.asyncio
async def test_publish_records_event_even_with_no_subscribers(repos, workspace):
    bus = EventBus(repos)
    event = await bus.publish(event_type="workflow_started", workspace_id=workspace.id, source_type="execution", source_id="exec-1", payload={"a": 1})
    assert event.id is not None
    stored = await repos.events.list_for_workspace(workspace.id)
    assert len(stored) == 1
    assert stored[0].payload == {"a": 1}


@pytest.mark.asyncio
async def test_internal_handler_subscription_is_invoked(repos, workspace):
    received = []

    async def handler(event):
        received.append(event.event_type)

    bus = EventBus(repos, internal_handlers={"log_it": handler})
    subs = SubscriptionService(repos)
    await subs.subscribe_internal_handler(workspace.id, "node_completed", handler_key="log_it", created_by="u1")

    await bus.publish(event_type="node_completed", workspace_id=workspace.id, source_type="node", source_id="n1")
    assert received == ["node_completed"]

    # a different event type must not trigger the handler
    await bus.publish(event_type="node_failed", workspace_id=workspace.id, source_type="node", source_id="n1")
    assert received == ["node_completed"]


@pytest.mark.asyncio
async def test_unregistered_handler_key_does_not_raise(repos, workspace):
    bus = EventBus(repos)
    subs = SubscriptionService(repos)
    await subs.subscribe_internal_handler(workspace.id, "node_completed", handler_key="missing", created_by="u1")
    # should not raise even though no handler is registered for "missing"
    await bus.publish(event_type="node_completed", workspace_id=workspace.id, source_type="node")


@pytest.mark.asyncio
async def test_webhook_subscription_delivers_via_mock_transport(repos, workspace):
    received_bodies = []

    def responder(request: httpx.Request) -> httpx.Response:
        received_bodies.append(request.content)
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(responder))
    bus = EventBus(repos, http_client=client)
    subs = SubscriptionService(repos)
    sub = await subs.subscribe_webhook(workspace.id, "workflow_completed", url="https://hooks.example.com/wf", created_by="u1")

    event = await bus.publish(event_type="workflow_completed", workspace_id=workspace.id, source_type="execution", source_id="exec-1")

    deliveries = await repos.webhook_deliveries.list_for_subscription(sub.id)
    assert len(deliveries) == 1
    assert deliveries[0].event_id == event.id
    assert deliveries[0].status == WebhookDeliveryStatus.DELIVERED.value
    assert deliveries[0].response_status_code == 200
    assert len(received_bodies) == 1
    await client.aclose()


@pytest.mark.asyncio
async def test_webhook_delivery_failure_is_recorded_not_raised(repos, workspace):
    def responder(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = httpx.AsyncClient(transport=httpx.MockTransport(responder))
    bus = EventBus(repos, http_client=client)
    subs = SubscriptionService(repos)
    await subs.subscribe_webhook(workspace.id, "workflow_failed", url="https://hooks.example.com/fail", created_by="u1")

    await bus.publish(event_type="workflow_failed", workspace_id=workspace.id, source_type="execution")

    deliveries = await repos.webhook_deliveries.list_for_subscription((await repos.subscriptions.list_for_workspace(workspace.id))[0].id)
    assert deliveries[0].status == WebhookDeliveryStatus.FAILED.value
    assert deliveries[0].response_status_code == 500
    await client.aclose()


@pytest.mark.asyncio
async def test_webhook_delivery_network_error_is_recorded_not_raised(repos, workspace):
    def responder(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    client = httpx.AsyncClient(transport=httpx.MockTransport(responder))
    bus = EventBus(repos, http_client=client)
    subs = SubscriptionService(repos)
    await subs.subscribe_webhook(workspace.id, "workflow_failed", url="https://unreachable.example.com", created_by="u1")

    await bus.publish(event_type="workflow_failed", workspace_id=workspace.id, source_type="execution")

    sub = (await repos.subscriptions.list_for_workspace(workspace.id))[0]
    deliveries = await repos.webhook_deliveries.list_for_subscription(sub.id)
    assert deliveries[0].status == WebhookDeliveryStatus.FAILED.value
    assert deliveries[0].error_message is not None
    await client.aclose()


@pytest.mark.asyncio
async def test_retry_pending_webhook_deliveries_redelivers_failed(repos, workspace):
    attempt_count = {"n": 0}

    def responder(request: httpx.Request) -> httpx.Response:
        attempt_count["n"] += 1
        if attempt_count["n"] == 1:
            return httpx.Response(503)
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(responder))
    bus = EventBus(repos, http_client=client)
    subs = SubscriptionService(repos)
    await subs.subscribe_webhook(workspace.id, "workflow_failed", url="https://hooks.example.com/retry", created_by="u1")

    await bus.publish(event_type="workflow_failed", workspace_id=workspace.id, source_type="execution")
    sub = (await repos.subscriptions.list_for_workspace(workspace.id))[0]
    first = await repos.webhook_deliveries.list_for_subscription(sub.id)
    assert first[0].status == WebhookDeliveryStatus.FAILED.value

    delivered_count = await bus.retry_pending_webhook_deliveries()
    assert delivered_count == 1

    after = await repos.webhook_deliveries.list_for_subscription(sub.id)
    assert after[0].status == WebhookDeliveryStatus.DELIVERED.value
    assert after[0].attempt_count == 2
    await client.aclose()


@pytest.mark.asyncio
async def test_deactivated_subscription_is_not_dispatched(repos, workspace):
    received = []

    async def handler(event):
        received.append(event)

    bus = EventBus(repos, internal_handlers={"h": handler})
    subs = SubscriptionService(repos)
    sub = await subs.subscribe_internal_handler(workspace.id, "custom", handler_key="h", created_by="u1")
    await subs.deactivate(sub.id)

    await bus.publish(event_type="custom", workspace_id=workspace.id, source_type="external")
    assert received == []


@pytest.mark.asyncio
async def test_subscription_service_validates_required_fields(repos, workspace):
    subs = SubscriptionService(repos)
    with pytest.raises(ValidationError):
        await subs.subscribe_webhook(workspace.id, "workflow_started", url="", created_by="u1")
    with pytest.raises(ValidationError):
        await subs.subscribe_internal_handler(workspace.id, "workflow_started", handler_key="", created_by="u1")
