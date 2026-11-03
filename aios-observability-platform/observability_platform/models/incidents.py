"""Incident management: `IncidentModel` is the guarded lifecycle
record; timeline events are an append-only audit trail of everything
that happened during the incident; postmortems are a separate
one-per-incident table since not every incident gets (or needs) one."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from observability_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, VersionedMixin, utcnow


class IncidentModel(IdMixin, AuditMixin, SoftDeleteMixin, VersionedMixin, Base):
    __tablename__ = "obs_incidents"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="sev3")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    component_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    alert_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    assigned_to: Mapped[str | None] = mapped_column(String(64), nullable=True)
    escalation_policy_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    root_cause: Mapped[str | None] = mapped_column(String(4000), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(String(4000), nullable=True)

    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class IncidentTimelineEventModel(IdMixin, Base):
    __tablename__ = "obs_incident_timeline_events"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    incident_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(String(4000), nullable=False)
    actor: Mapped[str | None] = mapped_column(String(64), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class IncidentPostmortemModel(IdMixin, AuditMixin, Base):
    __tablename__ = "obs_incident_postmortems"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    incident_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True, index=True)
    summary: Mapped[str] = mapped_column(String(4000), nullable=False)
    root_cause_analysis: Mapped[str | None] = mapped_column(String(8000), nullable=True)
    action_items: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    kb_links: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
