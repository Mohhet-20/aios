"""Webhook Platform: subscriptions, delivery attempts, replay."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from gateway_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_webhook_delivery_service,
    get_webhook_subscription_service,
)
from gateway_platform.gw_api.serialization import to_dict, to_dict_list
from gateway_platform.webhooks.delivery_service import WebhookDeliveryService
from gateway_platform.webhooks.subscription_service import WebhookSubscriptionService

router = APIRouter(prefix="/webhooks/subscriptions", tags=["webhook-platform"])


class CreateSubscriptionRequest(BaseModel):
    target_url: str
    event_types: list[str]


@router.post("", status_code=201)
async def create_webhook_subscription(
    body: CreateSubscriptionRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: WebhookSubscriptionService = Depends(get_webhook_subscription_service),
):
    result = await service.create_subscription(tenant_id, **body.model_dump())
    return {"subscription": to_dict(result.subscription), "raw_secret": result.raw_secret}


@router.get("")
async def list_webhook_subscriptions(tenant_id: str = Depends(get_current_tenant_id), service: WebhookSubscriptionService = Depends(get_webhook_subscription_service)):
    return to_dict_list(await service.list_for_tenant(tenant_id))


@router.post("/{subscription_id}/deactivate")
async def deactivate_webhook_subscription(
    subscription_id: str, tenant_id: str = Depends(get_current_tenant_id), service: WebhookSubscriptionService = Depends(get_webhook_subscription_service),
):
    return to_dict(await service.deactivate(tenant_id, subscription_id))


@router.post("/{subscription_id}/reactivate")
async def reactivate_webhook_subscription(
    subscription_id: str, tenant_id: str = Depends(get_current_tenant_id), service: WebhookSubscriptionService = Depends(get_webhook_subscription_service),
):
    return to_dict(await service.reactivate(tenant_id, subscription_id))


deliveries_router = APIRouter(prefix="/webhooks/deliveries", tags=["webhook-platform"])


class DispatchEventRequest(BaseModel):
    event_type: str
    payload: dict


@deliveries_router.post("/dispatch", status_code=201)
async def dispatch_webhook_event(
    body: DispatchEventRequest, tenant_id: str = Depends(get_current_tenant_id), service: WebhookDeliveryService = Depends(get_webhook_delivery_service),
):
    return to_dict_list(await service.dispatch_event(tenant_id, **body.model_dump()))


class AttemptDeliveryRequest(BaseModel):
    secret: str


@deliveries_router.post("/{delivery_id}/attempt")
async def attempt_webhook_delivery(
    delivery_id: str, body: AttemptDeliveryRequest, tenant_id: str = Depends(get_current_tenant_id),
    service: WebhookDeliveryService = Depends(get_webhook_delivery_service),
):
    return to_dict(await service.attempt_delivery(tenant_id, delivery_id, secret=body.secret))


@deliveries_router.post("/{delivery_id}/replay", status_code=201)
async def replay_webhook_delivery(
    delivery_id: str, tenant_id: str = Depends(get_current_tenant_id), service: WebhookDeliveryService = Depends(get_webhook_delivery_service),
):
    return to_dict(await service.replay_delivery(tenant_id, delivery_id))


@deliveries_router.get("/for-subscription/{subscription_id}")
async def list_deliveries_for_subscription(
    subscription_id: str, tenant_id: str = Depends(get_current_tenant_id), service: WebhookDeliveryService = Depends(get_webhook_delivery_service),
):
    return to_dict_list(await service.list_for_subscription(tenant_id, subscription_id))
