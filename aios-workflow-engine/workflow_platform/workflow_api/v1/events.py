"""Event System surface: publish events onto the bus, manage webhook/
internal-handler subscriptions, and retry failed webhook deliveries."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from workflow_platform.events.event_bus import EventBus
from workflow_platform.events.subscription_service import SubscriptionService
from workflow_platform.workflow_api.dependencies import get_event_bus, get_subscription_service
from workflow_platform.workflow_api.serialization import to_dict, to_dict_list

router = APIRouter(tags=["events"])


class PublishEventRequest(BaseModel):
    event_type: str
    workspace_id: str
    source_type: str
    source_id: str
    payload: dict = {}


class SubscribeWebhookRequest(BaseModel):
    event_type: str
    url: str
    created_by: str
    headers: dict | None = None


class SubscribeHandlerRequest(BaseModel):
    event_type: str
    handler_key: str
    created_by: str


@router.post("/events", status_code=201)
async def publish_event(body: PublishEventRequest, bus: EventBus = Depends(get_event_bus)):
    event = await bus.publish(
        event_type=body.event_type, workspace_id=body.workspace_id, source_type=body.source_type,
        source_id=body.source_id, payload=body.payload,
    )
    return to_dict(event)


@router.post("/events/webhook-deliveries/retry")
async def retry_webhook_deliveries(max_attempts: int = 5, limit: int = 100, bus: EventBus = Depends(get_event_bus)):
    count = await bus.retry_pending_webhook_deliveries(max_attempts=max_attempts, limit=limit)
    return {"retried_count": count}


@router.post("/subscriptions/webhook", status_code=201)
async def subscribe_webhook(workspace_id: str, body: SubscribeWebhookRequest, svc: SubscriptionService = Depends(get_subscription_service)):
    return to_dict(await svc.subscribe_webhook(workspace_id, body.event_type, url=body.url, created_by=body.created_by, headers=body.headers))


@router.post("/subscriptions/handler", status_code=201)
async def subscribe_handler(workspace_id: str, body: SubscribeHandlerRequest, svc: SubscriptionService = Depends(get_subscription_service)):
    return to_dict(await svc.subscribe_internal_handler(workspace_id, body.event_type, handler_key=body.handler_key, created_by=body.created_by))


@router.get("/subscriptions")
async def list_subscriptions(workspace_id: str, svc: SubscriptionService = Depends(get_subscription_service)):
    return to_dict_list(await svc.list_for_workspace(workspace_id))


@router.post("/subscriptions/{subscription_id}/deactivate")
async def deactivate_subscription(subscription_id: str, svc: SubscriptionService = Depends(get_subscription_service)):
    return to_dict(await svc.deactivate(subscription_id))


@router.post("/subscriptions/{subscription_id}/reactivate")
async def reactivate_subscription(subscription_id: str, svc: SubscriptionService = Depends(get_subscription_service)):
    return to_dict(await svc.reactivate(subscription_id))
