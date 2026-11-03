from __future__ import annotations

import pytest

from gateway_platform.core.exceptions import WebhookNotFoundError
from gateway_platform.webhooks.subscription_service import WebhookSubscriptionService, matches_event

TENANT = "wh-sub-tenant"


class _FakeSub:
    def __init__(self, event_types):
        self.event_types = event_types


def test_matches_event_exact_and_wildcard():
    assert matches_event(_FakeSub(["order.created"]), "order.created") is True
    assert matches_event(_FakeSub(["invoice.*"]), "order.created") is False
    assert matches_event(_FakeSub(["*"]), "order.created") is True


@pytest.mark.asyncio
async def test_create_subscription_returns_raw_secret_and_vault_ref(repos):
    service = WebhookSubscriptionService(repos)
    result = await service.create_subscription(
        TENANT, target_url="https://example.com/hook", event_types=["order.*"]
    )
    assert result.raw_secret
    assert result.subscription.secret_ref.startswith("vault://webhook-secrets/")


@pytest.mark.asyncio
async def test_deactivate_reactivate_update_filters(repos):
    service = WebhookSubscriptionService(repos)
    result = await service.create_subscription(
        TENANT, target_url="https://example.com/hook2", event_types=["invoice.*"]
    )
    sub_id = result.subscription.id

    deactivated = await service.deactivate(TENANT, sub_id)
    assert deactivated.is_active is False

    reactivated = await service.reactivate(TENANT, sub_id)
    assert reactivated.is_active is True

    updated = await service.update_filters(TENANT, sub_id, ["invoice.paid"])
    assert updated.event_types == ["invoice.paid"]


@pytest.mark.asyncio
async def test_list_active_and_list_for_tenant(repos):
    service = WebhookSubscriptionService(repos)
    result = await service.create_subscription(
        TENANT, target_url="https://example.com/hook3", event_types=["*"]
    )
    await service.deactivate(TENANT, result.subscription.id)
    another = await service.create_subscription(
        TENANT, target_url="https://example.com/hook4", event_types=["*"]
    )

    active = await service.list_active(TENANT)
    active_ids = {s.id for s in active}
    assert another.subscription.id in active_ids
    assert result.subscription.id not in active_ids

    all_for_tenant = await service.list_for_tenant(TENANT)
    assert len(all_for_tenant) >= 2


@pytest.mark.asyncio
async def test_not_found_raises_for_other_tenant(repos):
    service = WebhookSubscriptionService(repos)
    result = await service.create_subscription(
        TENANT, target_url="https://example.com/hook5", event_types=["*"]
    )
    with pytest.raises(WebhookNotFoundError):
        await service.deactivate("some-other-tenant", result.subscription.id)
