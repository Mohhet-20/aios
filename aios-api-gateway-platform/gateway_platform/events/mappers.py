"""ORM <-> domain-aggregate bridge for `EventMessage`."""
from __future__ import annotations

from gateway_platform.domain.entities import EventMessage
from gateway_platform.domain.enums import EventMessageStatus
from gateway_platform.models.events import EventMessageModel


def event_message_to_domain(model: EventMessageModel) -> EventMessage:
    return EventMessage(id=model.id, status=EventMessageStatus(model.status), delivered_at=model.delivered_at)


def apply_event_message_domain_to_model(entity: EventMessage, model: EventMessageModel) -> None:
    model.status = entity.status.value
    model.delivered_at = entity.delivered_at
