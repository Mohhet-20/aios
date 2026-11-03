"""Code Generation schema: a guarded generation job (queued -> running
-> completed/failed) targeting one output language/format against a
source spec (this platform's own OpenAPI schema, or a plugin/workflow
template), and the artifacts it produced."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from developer_platform.database.base import AuditMixin, Base, IdMixin, utcnow


class CodeGenJobModel(IdMixin, AuditMixin, Base):
    __tablename__ = "dev_codegen_jobs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target: Mapped[str] = mapped_column(String(30), nullable=False)
    source_spec_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="queued", index=True)
    requested_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class CodeGenArtifactModel(IdMixin, Base):
    __tablename__ = "dev_codegen_artifacts"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    job_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(100), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
