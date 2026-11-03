"""CLI Platform schema: authenticated CLI sessions (opaque token
issued to `aios login`) and a command execution log used for
diagnostics and developer analytics."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from developer_platform.database.base import AuditMixin, Base, IdMixin, utcnow


class CliSessionModel(IdMixin, AuditMixin, Base):
    __tablename__ = "dev_cli_sessions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    developer_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="active", index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CliCommandLogModel(IdMixin, Base):
    __tablename__ = "dev_cli_command_logs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    command: Mapped[str] = mapped_column(String(200), nullable=False)
    args: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    exit_code: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)
