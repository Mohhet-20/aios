"""Event System substrate: `EventModel` is the append-only event log
every workflow/node/agent/memory/tool/external occurrence gets published
to; `SubscriptionModel` registers interest (an internal handler or a
webhook URL) in a given `event_type`; `WebhookDeliveryModel` tracks each
actual HTTP delivery attempt for a webhook subscription, independent of
the event itself, since a delivery can fail and retry without the event
being re-published."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from workflow_platform.database.base import Base, IdMixin, utcnow
from workflow_platform.domain.enums import WebhookDeliveryStatus


class EventModel(Base, IdMixin):
    __tablename__ = "wf_events"

    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, doc="workflow | node | agent | memory | tool | external | schedule")
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class SubscriptionModel(Base, IdMixin):
    __tablename__ = "wf_subscriptions"

    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    target_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="{'url', 'headers'} for webhook; {'handler_key'} for internal_handler")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class WebhookDeliveryModel(Base, IdMixin):
    __tablename__ = "wf_webhook_deliveries"

    subscription_id: Mapped[str] = mapped_column(String(36), ForeignKey("wf_subscriptions.id"), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(36), ForeignKey("wf_events.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default=WebhookDeliveryStatus.PENDING.value, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    response_status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    delivered_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
