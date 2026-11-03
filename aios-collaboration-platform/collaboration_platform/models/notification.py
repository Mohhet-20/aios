"""ORM models for notifications, per-user/per-type delivery
preferences, and the delivery attempt log (one row per channel per
notification, so a failed email doesn't hide a successfully delivered
in-app notification)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from collaboration_platform.database.base import Base, IdMixin, utcnow
from collaboration_platform.domain.enums import DeliveryStatus


class NotificationModel(IdMixin, Base):
    __tablename__ = "cp_notifications"
    __table_args__ = (Index("ix_cp_notifications_recipient", "recipient_id"), Index("ix_cp_notifications_read", "recipient_id", "is_read"))

    recipient_id: Mapped[str] = mapped_column(String(36), nullable=False)
    notification_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    asset_id: Mapped[str | None] = mapped_column(ForeignKey("cp_assets.id"), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notification_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class NotificationPreferenceModel(IdMixin, Base):
    __tablename__ = "cp_notification_preferences"
    __table_args__ = (UniqueConstraint("user_id", "notification_type", name="uq_cp_notif_pref_user_type"),)

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    notification_type: Mapped[str] = mapped_column(String(40), nullable=False)
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    digest_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class NotificationDeliveryModel(IdMixin, Base):
    __tablename__ = "cp_notification_deliveries"
    __table_args__ = (Index("ix_cp_notif_delivery_notification", "notification_id"),)

    notification_id: Mapped[str] = mapped_column(ForeignKey("cp_notifications.id"), nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=DeliveryStatus.PENDING.value, nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
