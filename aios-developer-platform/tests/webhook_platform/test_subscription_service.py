import uuid

import pytest

from developer_platform.core.exceptions import WebhookNotFoundError
from developer_platform.webhook_platform.subscription_service import WebhookSubscriptionService, matches_event

def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_create_subscription_generates_secret_and_pointer(repos, db_session):
    tenant_id = _tid()
    service = WebhookSubscriptionService(repos)
    result = await service.create_subscription(tenant_id, target_url="https://example.com/hook", event_types=["sdk_call"])
    await db_session.commit()

    assert result.subscription.is_active is True
    assert result.subscription.secret_ref is not None
    assert len(result.raw_secret) > 10

    stored_secret_ref = await repos.secret_references.get_or_404(result.subscription.secret_ref)
    assert stored_secret_ref.material_ref != result.raw_secret  # raw secret is never persisted


@pytest.mark.asyncio
async def test_deactivate_and_reactivate(repos, db_session):
    tenant_id = _tid()
    service = WebhookSubscriptionService(repos)
    result = await service.create_subscription(tenant_id, target_url="https://example.com/hook", event_types=["*"])
    await db_session.commit()

    deactivated = await service.deactivate(result.subscription.id)
    await db_session.commit()
    assert deactivated.is_active is False

    active = await service.list_active(tenant_id)
    assert deactivated.id not in [s.id for s in active]

    reactivated = await service.reactivate(result.subscription.id)
    await db_session.commit()
    assert reactivated.is_active is True


@pytest.mark.asyncio
async def test_deactivate_unknown_subscription_raises(repos, db_session):
    service = WebhookSubscriptionService(repos)
    with pytest.raises(WebhookNotFoundError):
        await service.deactivate("not-a-real-id")


@pytest.mark.asyncio
async def test_update_filters(repos, db_session):
    tenant_id = _tid()
    service = WebhookSubscriptionService(repos)
    result = await service.create_subscription(tenant_id, target_url="https://example.com/hook", event_types=["sdk_call"])
    await db_session.commit()

    updated = await service.update_filters(result.subscription.id, ["sdk_call", "api_call"])
    await db_session.commit()
    assert updated.event_types == ["sdk_call", "api_call"]


def test_matches_event_wildcard_and_exact():
    class _Fake:
        event_types = ["sdk_call"]

    assert matches_event(_Fake(), "sdk_call") is True
    assert matches_event(_Fake(), "api_call") is False

    class _Wildcard:
        event_types = ["*"]

    assert matches_event(_Wildcard(), "anything") is True
