import uuid
from datetime import timedelta

import pytest

from developer_platform.config.settings import Settings
from developer_platform.database.base import utcnow
from developer_platform.webhook_platform.delivery_service import WebhookDeliveryService
from developer_platform.webhook_platform.subscription_service import WebhookSubscriptionService

pytestmark = pytest.mark.asyncio


def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


def _ok_sender(url, payload, signature):
    return True, None


def _fail_sender(url, payload, signature):
    return False, "connection refused"


async def test_dispatch_event_fans_out_to_matching_active_subscriptions(repos, db_session):
    tenant_id = _tid()
    subs = WebhookSubscriptionService(repos)
    delivery = WebhookDeliveryService(repos)

    matching = await subs.create_subscription(tenant_id, target_url="https://a.example.com", event_types=["sdk_call"])
    await subs.create_subscription(tenant_id, target_url="https://b.example.com", event_types=["api_call"])
    inactive = await subs.create_subscription(tenant_id, target_url="https://c.example.com", event_types=["sdk_call"])
    await db_session.commit()
    await subs.deactivate(inactive.subscription.id)
    await db_session.commit()

    deliveries = await delivery.dispatch_event(tenant_id, event_type="sdk_call", payload={"foo": "bar"})
    await db_session.commit()

    assert len(deliveries) == 1
    assert deliveries[0].subscription_id == matching.subscription.id


async def test_attempt_delivery_success(repos, db_session):
    tenant_id = _tid()
    subs = WebhookSubscriptionService(repos)
    delivery = WebhookDeliveryService(repos)

    result = await subs.create_subscription(tenant_id, target_url="https://a.example.com", event_types=["*"])
    await db_session.commit()
    [created] = await delivery.dispatch_event(tenant_id, event_type="api_call", payload={"x": 1})
    await db_session.commit()

    delivered = await delivery.attempt_delivery(tenant_id, created.id, secret=result.raw_secret, sender=_ok_sender)
    await db_session.commit()
    assert delivered.status == "succeeded"
    assert delivered.delivered_at is not None
    assert delivered.attempt_count == 1


async def test_attempt_delivery_failure_schedules_retry(repos, db_session):
    tenant_id = _tid()
    subs = WebhookSubscriptionService(repos)
    delivery = WebhookDeliveryService(repos)

    result = await subs.create_subscription(tenant_id, target_url="https://a.example.com", event_types=["*"])
    await db_session.commit()
    [created] = await delivery.dispatch_event(tenant_id, event_type="api_call", payload={"x": 1})
    await db_session.commit()

    failed = await delivery.attempt_delivery(tenant_id, created.id, secret=result.raw_secret, sender=_fail_sender)
    await db_session.commit()
    assert failed.status == "failed"
    assert failed.last_error == "connection refused"
    assert failed.next_attempt_at is not None
    assert failed.attempt_count == 1


async def test_delivery_exhausts_after_max_retries(repos, db_session):
    tenant_id = _tid()
    settings = Settings(database_url="sqlite+aiosqlite:///:memory:", secret_key="x" * 32, webhook_max_retry_attempts=2)
    subs = WebhookSubscriptionService(repos)
    delivery = WebhookDeliveryService(repos, settings=settings)

    result = await subs.create_subscription(tenant_id, target_url="https://a.example.com", event_types=["*"])
    await db_session.commit()
    [created] = await delivery.dispatch_event(tenant_id, event_type="api_call", payload={"x": 1})
    await db_session.commit()

    first = await delivery.attempt_delivery(tenant_id, created.id, secret=result.raw_secret, sender=_fail_sender)
    await db_session.commit()
    assert first.status == "failed"

    second = await delivery.attempt_delivery(tenant_id, created.id, secret=result.raw_secret, sender=_fail_sender)
    await db_session.commit()
    assert second.status == "exhausted"
    assert second.next_attempt_at is None


async def test_replay_delivery_creates_new_row(repos, db_session):
    tenant_id = _tid()
    subs = WebhookSubscriptionService(repos)
    delivery = WebhookDeliveryService(repos)

    result = await subs.create_subscription(tenant_id, target_url="https://a.example.com", event_types=["*"])
    await db_session.commit()
    [created] = await delivery.dispatch_event(tenant_id, event_type="api_call", payload={"x": 1})
    await db_session.commit()
    await delivery.attempt_delivery(tenant_id, created.id, secret=result.raw_secret, sender=_fail_sender)
    await db_session.commit()

    replayed = await delivery.replay_delivery(tenant_id, created.id)
    await db_session.commit()

    assert replayed.id != created.id
    assert replayed.status == "pending"
    assert replayed.attempt_count == 0
    assert replayed.payload == created.payload

    history = await delivery.list_for_subscription(tenant_id, created.subscription_id)
    assert len(history) == 2


async def test_sweep_retries_processes_due_deliveries(repos, db_session):
    tenant_id = _tid()
    subs = WebhookSubscriptionService(repos)
    delivery = WebhookDeliveryService(repos)

    result = await subs.create_subscription(tenant_id, target_url="https://a.example.com", event_types=["*"])
    await db_session.commit()
    [created] = await delivery.dispatch_event(tenant_id, event_type="api_call", payload={"x": 1})
    await db_session.commit()
    await delivery.attempt_delivery(tenant_id, created.id, secret=result.raw_secret, sender=_fail_sender)
    await db_session.commit()

    # Backdate next_attempt_at so the sweep considers it due right now.
    record = await repos.webhook_deliveries.get_or_404(created.id)
    record.next_attempt_at = utcnow() - timedelta(seconds=1)
    await repos.webhook_deliveries.update(record)
    await db_session.commit()

    swept = await delivery.sweep_retries(tenant_id, secret_lookup=lambda ref: result.raw_secret, sender=_ok_sender)
    await db_session.commit()

    assert len(swept) == 1
    assert swept[0].status == "succeeded"
