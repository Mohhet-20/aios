"""Container image registry schema: images (guarded lifecycle:
building -> scanning -> signed/scan_failed -> published -> deprecated/
quarantined), scan results (append-only, one row per scan), and
signatures (append-only, one row per signing event)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infra_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class ContainerImageModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "infra_container_images"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    repository: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    tag: Mapped[str] = mapped_column(String(100), nullable=False)
    digest: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="building", index=True)
    built_from_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    signed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class ImageScanResultModel(IdMixin, Base):
    __tablename__ = "infra_image_scan_results"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    image_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    finding_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class ImageSignatureModel(IdMixin, Base):
    __tablename__ = "infra_image_signatures"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    image_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    signer: Mapped[str] = mapped_column(String(200), nullable=False)
    signature: Mapped[str] = mapped_column(String(1000), nullable=False)
    signed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
