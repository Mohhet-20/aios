"""AlertRuleModel: a standing condition (metric/threshold/comparator/
window, or a fully custom rule) evaluated on a schedule; when it trips,
it produces an `AlertModel` row and (optionally) dispatches through a
notification policy. Alert lifecycle is OPEN -> ACKNOWLEDGED ->
RESOLVED, mirroring an on-call incident, not a fire-and-forget log
line."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from eval_platform.database.base import AuditMixin, Base, IdMixin, utcnow
from eval_platform.domain.enums import AlertStatus


class AlertRuleModel(Base, IdMixin, AuditMixin):
    __tablename__ = "ep_alert_rules"

    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    condition: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc='{"metric": "...", "comparator": "gt", "threshold": 0.5, "window_minutes": 60}')
    notification_policy: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="Bridge target(s) to notify — see platform_bridges")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class AlertModel(Base, IdMixin):
    __tablename__ = "ep_alerts"

    alert_rule_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ep_alert_rules.id"), nullable=True, index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=AlertStatus.OPEN.value, nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    context: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    triggered_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    acknowledged_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    acknowledged_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    resolved_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
