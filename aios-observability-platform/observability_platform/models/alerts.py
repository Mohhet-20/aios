"""Alerting: rules define WHEN to fire, alerts ARE a fired instance
(guarded lifecycle: firing -> acknowledged/resolved, or firing ->
suppressed), escalation policies + escalation records track who got
notified and when, maintenance windows suppress alerts for a
component during planned work, and notification channels/deliveries
record the actual fan-out attempts."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from observability_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, VersionedMixin, utcnow


class AlertRuleModel(IdMixin, AuditMixin, SoftDeleteMixin, VersionedMixin, Base):
    __tablename__ = "obs_alert_rules"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    component_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    metric_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    condition: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    evaluation_window_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    escalation_policy_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class AlertModel(IdMixin, AuditMixin, VersionedMixin, Base):
    __tablename__ = "obs_alerts"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rule_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    alert_type: Mapped[str] = mapped_column(String(30), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="firing", index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    component_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    dedup_key: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    fired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suppressed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class EscalationPolicyModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "obs_escalation_policies"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    levels: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # levels: [{"level": 1, "delay_minutes": 0, "targets": ["channel-id-1"]}, ...]


class AlertEscalationModel(IdMixin, Base):
    __tablename__ = "obs_alert_escalations"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    alert_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False)
    level: Mapped[int] = mapped_column(Integer, nullable=False)
    target: Mapped[str] = mapped_column(String(300), nullable=False)
    escalated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class MaintenanceWindowModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "obs_maintenance_windows"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    component_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="scheduled")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    suppress_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reason: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class NotificationChannelModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "obs_notification_channels"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    channel_type: Mapped[str] = mapped_column(String(20), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class AlertNotificationModel(IdMixin, Base):
    __tablename__ = "obs_alert_notifications"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    alert_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    channel_id: Mapped[str] = mapped_column(String(36), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
