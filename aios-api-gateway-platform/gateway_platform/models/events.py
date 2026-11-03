"""Event Platform schema: topics (one per event stream, categorized
by the taxonomy the prompt specifies — workflow/agent/prompt/security/
system/custom), subscriptions binding a subscriber to a topic with an
optional filter, published messages with a guarded lifecycle
(published -> delivered/failed, failed re-entering via retry up to a
max attempt count before being moved to the dead letter table), and a
dedicated dead-letter table so DLQ inspection/replay doesn't have to
scan the full message history."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from gateway_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class EventTopicModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "gw_event_topics"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(20), nullable=False, default="custom", index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="active", index=True)


class EventSubscriptionModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "gw_event_subscriptions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    topic_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subscriber: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="active", index=True)
    event_filter: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class EventMessageModel(IdMixin, Base):
    __tablename__ = "gw_event_messages"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    topic_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="published", index=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DeadLetterEntryModel(IdMixin, Base):
    __tablename__ = "gw_dead_letter_entries"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    message_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    topic_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    moved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
