from __future__ import annotations

import pytest

from gateway_platform.webhooks.delivery_service import WebhookDeliveryService
from gateway_platform.webhooks.subscription_service import WebhookSubscriptionService

TENANT = "wh-delivery-tenant"


def _ok_sender(url, payload, signature):
    return True, None


def _fail_sender(url, payload, signature):
    return False, "HTTP 500"


@pytest.mark.asyncio
async def test_dispatch_event_fans_out_to_matching_active_subscriptions(repos):
    subs = WebhookSubscriptionService(repos)
    matching = await subs.create_subscription(TENANT, target_url="https://a.example/hook", event_types=["order.created"])
    non_matching = await subs.create_subscription(TENANT, target_url="https://b.example/hook", event_types=["invoice.paid"])

    deliveries = WebhookDeliveryService(repos)
    created = await deliveries.dispatch_event(TENANT, event_type="order.created", payload={"id": 1})

    sub_ids = {d.subscription_id for d in created}
    assert matching.subscription.id in sub_ids
    assert non_matching.subscription.id not in sub_ids


@pytest.mark.asyncio
async def test_attempt_delivery_success_path(repos):
    subs = WebhookSubscriptionService(repos)
    sub = await subs.create_subscription(TENANT, target_url="https://a.example/hook", event_types=["*"])
    deliveries = WebhookDeliveryService(repos)
    created = await deliveries.dispatch_event(TENANT, event_type="ping", payload={"ok": True})
    delivery = created[0]

    result = await deliveries.attempt_delivery(TENANT, delivery.id, secret=sub.raw_secret, sender=_ok_sender)
    assert result.status == "delivered"
    assert result.attempt_count == 1


@pytest.mark.asyncio
async def test_attempt_delivery_failure_then_dead_letter_progression(repos):
    subs = WebhookSubscriptionService(repos)
    sub = await subs.create_subscription(TENANT, target_url="https://a.example/hook", event_types=["*"])
    deliveries = WebhookDeliveryService(repos)
    created = await deliveries.dispatch_event(TENANT, event_type="ping", payload={"ok": False})
    delivery_id = created[0].id

    first = await deliveries.attempt_delivery(TENANT, delivery_id, secret=sub.raw_secret, sender=_fail_sender)
    assert first.status == "retrying"

    last = first
    for _ in range(10):
        last = await deliveries.attempt_delivery(TENANT, delivery_id, secret=sub.raw_secret, sender=_fail_sender)
        if last.status == "dead_lettered":
            break
    assert last.status == "dead_lettered"


@pytest.mark.asyncio
async def test_list_due_for_retry_and_sweep_retries(repos):
    subs = WebhookSubscriptionService(repos)
    sub = await subs.create_subscription(TENANT, target_url="https://a.example/hook", event_types=["*"])
    deliveries = WebhookDeliveryService(repos)
    created = await deliveries.dispatch_event(TENANT, event_type="ping", payload={"ok": False})
    delivery_id = created[0].id

    await deliveries.attempt_delivery(TENANT, delivery_id, secret=sub.raw_secret, sender=_fail_sender)

    due = await deliveries.list_due_for_retry(TENANT)
    assert any(d.id == delivery_id for d in due)

    def secret_lookup(secret_ref: str) -> str:
        return sub.raw_secret

    results = await deliveries.sweep_retries(TENANT, secret_lookup=secret_lookup, sender=_ok_sender)
    assert any(r.id == delivery_id and r.status == "delivered" for r in results)


@pytest.mark.asyncio
async def test_replay_delivery_creates_fresh_row(repos):
    subs = WebhookSubscriptionService(repos)
    sub = await subs.create_subscription(TENANT, target_url="https://a.example/hook", event_types=["*"])
    deliveries = WebhookDeliveryService(repos)
    created = await deliveries.dispatch_event(TENANT, event_type="ping", payload={"ok": True})
    original_id = created[0].id
    await deliveries.attempt_delivery(TENANT, original_id, secret=sub.raw_secret, sender=_ok_sender)

    replayed = await deliveries.replay_delivery(TENANT, original_id)
    assert replayed.id != original_id
    assert replayed.status == "pending"

    for_sub = await deliveries.list_for_subscription(TENANT, sub.subscription.id)
    assert len(for_sub) >= 2
