"""API & SDK Documentation and Automation schema: API doc entries
across four protocol types, SDK doc entries across ten SDK/CLI
targets, and generation jobs (guarded queued -> running ->
completed/failed) that automate producing API/schema/config/SDK docs,
changelogs, dependency reports, architecture reports, and code
reference material."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from docs_platform.database.base import AuditMixin, Base, IdMixin, utcnow


class ApiDocEntryModel(IdMixin, AuditMixin, Base):
    __tablename__ = "doc_api_entries"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    protocol_type: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(300), nullable=False, index=True)
    method: Mapped[str | None] = mapped_column(String(10), nullable=True)
    summary: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    request_example: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    response_example: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    auth_example: Mapped[str] = mapped_column(Text, nullable=False, default="")
    error_docs: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    version: Mapped[str] = mapped_column(String(30), nullable=False, default="v1")


class SdkDocEntryModel(IdMixin, AuditMixin, Base):
    __tablename__ = "doc_sdk_entries"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    sdk_language: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    package_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[str] = mapped_column(String(30), nullable=False, default="v1")


class GenerationJobModel(IdMixin, AuditMixin, Base):
    __tablename__ = "doc_generation_jobs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    job_type: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    target_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="queued", index=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    result: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
