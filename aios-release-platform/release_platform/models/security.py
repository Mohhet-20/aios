"""Security & Supply Chain schema: SBOM records, artifact signatures,
and the release-approval workflow that gates a release from advancing
to `released` status under governance settings."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from release_platform.database.base import Base, IdMixin, utcnow


class SbomModel(IdMixin, Base):
    __tablename__ = "rel_sboms"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    artifact_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    format: Mapped[str] = mapped_column(String(30), nullable=False, default="cyclonedx")
    content_ref: Mapped[str] = mapped_column(Text, nullable=False, default="")
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ArtifactSignatureModel(IdMixin, Base):
    __tablename__ = "rel_artifact_signatures"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    artifact_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    algorithm: Mapped[str] = mapped_column(String(20), nullable=False, default="sha256")
    signed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ReleaseApprovalModel(IdMixin, Base):
    __tablename__ = "rel_release_approvals"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    release_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    approver_id: Mapped[str] = mapped_column(String(36), nullable=False)
    decision: Mapped[str] = mapped_column(String(15), nullable=False, default="pending", index=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
