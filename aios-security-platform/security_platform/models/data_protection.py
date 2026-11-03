"""PII / DLP schema. `PiiFindingModel` never stores the raw sensitive
value — only a hash (for dedup/audit correlation) and a short redacted
preview — the same "never persist what you don't need" discipline as
share-link tokens elsewhere in the AIOS build."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from security_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class PiiFindingModel(IdMixin, Base):
    __tablename__ = "sec_pii_findings"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    redacted_preview: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class DataClassificationModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "sec_data_classifications"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    sensitivity: Mapped[str] = mapped_column(String(20), nullable=False, default="internal")
    classified_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    rationale: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class DlpPolicyModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "sec_dlp_policies"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    sensitivity_threshold: Mapped[str] = mapped_column(String(20), nullable=False, default="confidential")
    action: Mapped[str] = mapped_column(String(10), nullable=False, default="flag")
    scope: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class DlpIncidentModel(IdMixin, Base):
    __tablename__ = "sec_dlp_incidents"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    action_taken: Mapped[str] = mapped_column(String(10), nullable=False, default="flag")
    details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
