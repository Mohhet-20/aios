"""Webhooks schema (Integration Hub's outbound-delivery surface):
identical subscription/delivery shape to every prior AIOS platform's
own webhook module — a subscription with a signing secret reference
and event-type filter, and a guarded per-event delivery record."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from gateway_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class WebhookSubscriptionModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "gw_webhook_subscriptions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_url: Mapped[str] = mapped_column(String(500), nullable=False)
    secret_ref: Mapped[str] = mapped_column(String(36), nullable=False)
    event_types: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class WebhookDeliveryModel(IdMixin, Base):
    __tablename__ = "gw_webhook_deliveries"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subscription_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="pending", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
