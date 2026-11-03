"""Compliance architecture: which frameworks a tenant has configured,
evidence collected against specific controls, retention policies,
legal holds (which take precedence over retention — see
`compliance/`'s module docstring), consent records, and data-residency
tracking."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from security_platform.database.base import AuditMixin, Base, IdMixin, utcnow


class ComplianceFrameworkConfigModel(IdMixin, AuditMixin, Base):
    __tablename__ = "sec_compliance_frameworks"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    framework: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class ComplianceEvidenceModel(IdMixin, Base):
    __tablename__ = "sec_compliance_evidence"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    framework: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    control_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    evidence_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    resource_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RetentionPolicyModel(IdMixin, AuditMixin, Base):
    __tablename__ = "sec_retention_policies"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=365)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class LegalHoldModel(IdMixin, AuditMixin, Base):
    __tablename__ = "sec_legal_holds"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    reason: Mapped[str] = mapped_column(String(2000), nullable=False)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConsentRecordModel(IdMixin, AuditMixin, Base):
    __tablename__ = "sec_consent_records"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subject_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    purpose: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="granted")
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class DataResidencyRecordModel(IdMixin, Base):
    __tablename__ = "sec_data_residency_records"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(20), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
