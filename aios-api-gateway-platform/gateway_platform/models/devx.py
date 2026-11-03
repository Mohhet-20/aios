"""Developer Experience schema: SDK/client code generation jobs
(reusing the same guarded queued -> running -> completed/failed
lifecycle every prior AIOS platform's own code-gen module uses) and a
record of every API Explorer / testing-console request a developer
fires against a route, so "try it out" activity is inspectable."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from gateway_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class SdkGenJobModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "gw_sdk_gen_jobs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    api_version: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="queued", index=True)
    artifact_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    error: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class TestConsoleRequestModel(IdMixin, Base):
    __tablename__ = "gw_test_console_requests"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    route_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    request_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    response_payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
