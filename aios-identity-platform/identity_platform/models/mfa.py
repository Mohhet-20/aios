"""MFA factors (TOTP today, `factor_type` is extensible), one-time
recovery codes (hashed, single-use), and trusted/remembered devices
that let a verified device skip a fresh MFA challenge until its
`expires_at`."""
from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from identity_platform.database.base import Base, IdMixin, utcnow
from identity_platform.domain.enums import MfaFactorStatus


class MfaFactorModel(Base, IdMixin):
    __tablename__ = "ip_mfa_factors"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_users.id"), nullable=False, index=True)
    factor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    secret_encrypted: Mapped[str] = mapped_column(String(500), nullable=False, doc="Fernet-encrypted TOTP shared secret")
    status: Mapped[str] = mapped_column(String(20), default=MfaFactorStatus.PENDING.value, nullable=False, index=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    verified_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RecoveryCodeModel(Base, IdMixin):
    __tablename__ = "ip_recovery_codes"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_users.id"), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    used_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TrustedDeviceModel(Base, IdMixin):
    __tablename__ = "ip_trusted_devices"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_users.id"), nullable=False, index=True)
    device_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    device_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(400), nullable=True)
    trusted_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_seen_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)
