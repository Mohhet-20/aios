"""Release & Version Management schema: releases with a guarded
editorial lifecycle, an append-only version history log, and a
compatibility matrix mapping a version to the range of a component
it's compatible with."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from release_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class ReleaseModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "rel_releases"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="draft", index=True)
    release_branch: Mapped[str | None] = mapped_column(String(120), nullable=True)
    build_metadata: Mapped[str | None] = mapped_column(String(120), nullable=True)
    changelog: Mapped[str] = mapped_column(Text, nullable=False, default="")
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VersionHistoryModel(IdMixin, Base):
    __tablename__ = "rel_version_history"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    release_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")


class CompatibilityEntryModel(IdMixin, Base):
    __tablename__ = "rel_compatibility_entries"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    component_ref: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    compatible_from: Mapped[str] = mapped_column(String(64), nullable=False)
    compatible_to: Mapped[str | None] = mapped_column(String(64), nullable=True)
    notes: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
