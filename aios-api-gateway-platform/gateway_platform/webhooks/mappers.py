"""ORM <-> domain-aggregate bridge for `WebhookDelivery`."""
from __future__ import annotations

from gateway_platform.domain.entities import WebhookDelivery
from gateway_platform.domain.enums import WebhookDeliveryStatus
from gateway_platform.models.webhooks import WebhookDeliveryModel


def webhook_delivery_to_domain(model: WebhookDeliveryModel) -> WebhookDelivery:
    return WebhookDelivery(id=model.id, status=WebhookDeliveryStatus(model.status), delivered_at=model.delivered_at)


def apply_webhook_delivery_domain_to_model(entity: WebhookDelivery, model: WebhookDeliveryModel) -> None:
    model.status = entity.status.value
    model.delivered_at = entity.delivered_at
