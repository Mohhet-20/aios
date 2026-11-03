"""Event Platform: topics, subscriptions, publish/deliver/retry/replay."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from gateway_platform.dependencies.dependencies import (
    get_current_tenant_id,
    get_event_bus_service,
    get_event_subscription_service,
    get_event_topic_service,
)
from gateway_platform.events.event_bus_service import EventBusService
from gateway_platform.events.subscription_service import EventSubscriptionService
from gateway_platform.events.topic_service import EventTopicService
from gateway_platform.gw_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/events/topics", tags=["event-platform"])


class RegisterTopicRequest(BaseModel):
    name: str
    category: str = "custom"


@router.post("", status_code=201)
async def register_topic(
    body: RegisterTopicRequest, tenant_id: str = Depends(get_current_tenant_id), service: EventTopicService = Depends(get_event_topic_service),
):
    return to_dict(await service.register_topic(tenant_id, **body.model_dump()))


@router.get("")
async def list_topics(tenant_id: str = Depends(get_current_tenant_id), service: EventTopicService = Depends(get_event_topic_service)):
    return to_dict_list(await service.list_for_tenant(tenant_id))


@router.post("/{topic_id}/pause")
async def pause_topic(
    topic_id: str, tenant_id: str = Depends(get_current_tenant_id), service: EventTopicService = Depends(get_event_topic_service),
):
    return to_dict(await service.pause_topic(tenant_id, topic_id))


@router.post("/{topic_id}/resume")
async def resume_topic(
    topic_id: str, tenant_id: str = Depends(get_current_tenant_id), service: EventTopicService = Depends(get_event_topic_service),
):
    return to_dict(await service.resume_topic(tenant_id, topic_id))


subscriptions_router = APIRouter(prefix="/events/subscriptions", tags=["event-platform"])


class SubscribeRequest(BaseModel):
    topic_id: str
    subscriber: str
    event_filter: dict | None = None


@subscriptions_router.post("", status_code=201)
async def subscribe(
    body: SubscribeRequest, tenant_id: str = Depends(get_current_tenant_id), service: EventSubscriptionService = Depends(get_event_subscription_service),
):
    return to_dict(await service.subscribe(tenant_id, body.topic_id, subscriber=body.subscriber, event_filter=body.event_filter))


@subscriptions_router.get("/for-topic/{topic_id}")
async def list_subscriptions(
    topic_id: str, active_only: bool = False, tenant_id: str = Depends(get_current_tenant_id),
    service: EventSubscriptionService = Depends(get_event_subscription_service),
):
    return to_dict_list(await service.list_for_topic(tenant_id, topic_id, active_only=active_only))


@subscriptions_router.post("/{subscription_id}/pause")
async def pause_subscription(
    subscription_id: str, tenant_id: str = Depends(get_current_tenant_id), service: EventSubscriptionService = Depends(get_event_subscription_service),
):
    return to_dict(await service.pause(tenant_id, subscription_id))


@subscriptions_router.post("/{subscription_id}/resume")
async def resume_subscription(
    subscription_id: str, tenant_id: str = Depends(get_current_tenant_id), service: EventSubscriptionService = Depends(get_event_subscription_service),
):
    return to_dict(await service.resume(tenant_id, subscription_id))


@subscriptions_router.post("/{subscription_id}/cancel")
async def cancel_subscription(
    subscription_id: str, tenant_id: str = Depends(get_current_tenant_id), service: EventSubscriptionService = Depends(get_event_subscription_service),
):
    return to_dict(await service.cancel(tenant_id, subscription_id))


messages_router = APIRouter(prefix="/events/messages", tags=["event-platform"])


class PublishEventRequest(BaseModel):
    topic_id: str
    payload: dict


@messages_router.post("/publish", status_code=201)
async def publish_event(
    body: PublishEventRequest, tenant_id: str = Depends(get_current_tenant_id), service: EventBusService = Depends(get_event_bus_service),
):
    return to_dict(await service.publish(tenant_id, body.topic_id, payload=body.payload))


@messages_router.post("/{message_id}/attempt-delivery")
async def attempt_delivery(
    message_id: str, tenant_id: str = Depends(get_current_tenant_id), service: EventBusService = Depends(get_event_bus_service),
):
    return to_dict(await service.attempt_delivery(tenant_id, message_id))


@messages_router.post("/{message_id}/retry")
async def retry_event(
    message_id: str, tenant_id: str = Depends(get_current_tenant_id), service: EventBusService = Depends(get_event_bus_service),
):
    return to_dict(await service.retry(tenant_id, message_id))


@messages_router.post("/{message_id}/replay", status_code=201)
async def replay_event(
    message_id: str, tenant_id: str = Depends(get_current_tenant_id), service: EventBusService = Depends(get_event_bus_service),
):
    return to_dict(await service.replay(tenant_id, message_id))


@messages_router.get("/for-topic/{topic_id}")
async def list_messages(
    topic_id: str, tenant_id: str = Depends(get_current_tenant_id), service: EventBusService = Depends(get_event_bus_service),
):
    return to_dict_list(await service.list_for_topic(tenant_id, topic_id))


@messages_router.get("/for-topic/{topic_id}/dead-letters")
async def list_dead_letters(
    topic_id: str, tenant_id: str = Depends(get_current_tenant_id), service: EventBusService = Depends(get_event_bus_service),
):
    return to_dict_list(await service.list_dead_letters(tenant_id, topic_id))
