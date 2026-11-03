"""Gateway core schema: the API route registry every request is
matched against. One row per (path, method, protocol) triple; the
guarded draft -> active -> deprecated -> retired lifecycle mirrors the
API Management module's version lifecycle but is scoped to a single
route rather than the whole API surface."""
from __future__ import annotations

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from gateway_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class ApiRouteModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "gw_api_routes"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False, default="GET")
    protocol: Mapped[str] = mapped_column(String(20), nullable=False, default="rest", index=True)
    visibility: Mapped[str] = mapped_column(String(20), nullable=False, default="internal", index=True)
    target_service: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="draft", index=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=30000)
    tags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
