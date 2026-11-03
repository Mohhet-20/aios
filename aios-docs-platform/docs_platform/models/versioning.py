"""Versioning & Release Notes schema: immutable content snapshots per
page version, release notes, and deprecation notices (with an
optional planned removal date, giving downstream consumers a
migration window)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from docs_platform.database.base import Base, IdMixin, utcnow


class DocVersionModel(IdMixin, Base):
    __tablename__ = "doc_versions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    page_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    content_snapshot: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ReleaseNoteModel(IdMixin, Base):
    __tablename__ = "doc_release_notes"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_label: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    kind: Mapped[str] = mapped_column(String(20), nullable=False, default="feature", index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    released_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class DeprecationNoticeModel(IdMixin, Base):
    __tablename__ = "doc_deprecation_notices"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subject_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    message: Mapped[str] = mapped_column(String(2000), nullable=False, default="")
    deprecated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    removal_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
