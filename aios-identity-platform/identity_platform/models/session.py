"""SessionModel: one authenticated session, keyed by a hashed refresh
token (never stored raw — see `sessions/token_service.py`). Concurrent-
session limits, revocation, and expiration all operate on this table.
`LoginHistoryModel` is the append-only record of every login attempt
(success or failure) a risk-scoring/anomaly-detection pass reads."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from identity_platform.database.base import Base, IdMixin, utcnow
from identity_platform.domain.enums import SessionStatus


class SessionModel(Base, IdMixin):
    __tablename__ = "ip_sessions"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_users.id"), nullable=False, index=True)
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True, doc="Active org context for this session, if any")
    refresh_token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default=SessionStatus.ACTIVE.value, nullable=False, index=True)

    device_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(400), nullable=True)

    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_used_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)


class LoginHistoryModel(Base, IdMixin):
    __tablename__ = "ip_login_history"

    user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True, doc="Null when the attempted email never resolved to a real user")
    email_attempted: Mapped[str] = mapped_column(String(320), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, index=True)
    failure_reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    mfa_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(400), nullable=True)
    geo_country: Mapped[str | None] = mapped_column(String(4), nullable=True)
    risk_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    risk_signals: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
