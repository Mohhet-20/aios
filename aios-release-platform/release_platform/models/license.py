"""License Management schema: enterprise/organization/trial/feature/
seat-based licenses with seat and feature-entitlement tracking."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from release_platform.database.base import AuditMixin, Base, IdMixin


class LicenseModel(IdMixin, AuditMixin, Base):
    __tablename__ = "rel_licenses"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    org_ref: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    license_type: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="active", index=True)
    seats_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    seats_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    features: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
