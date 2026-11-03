"""Password credential + the three short-lived, single-use token types
that drive password reset, email verification, and magic-link sign-in.
Every token is stored as a hash (`token_hash`), never the raw secret —
the raw value only ever exists in the response returned to the caller
at issuance time and whatever transport (email) carries it from there,
mirroring how `PasswordCredentialModel.password_hash` never stores a
plaintext password."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from identity_platform.database.base import Base, IdMixin, utcnow


class PasswordCredentialModel(Base, IdMixin):
    __tablename__ = "ip_password_credentials"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_users.id"), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(300), nullable=False)
    password_algorithm: Mapped[str] = mapped_column(String(30), default="pbkdf2_sha256", nullable=False)
    password_updated_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    must_change_password: Mapped[bool] = mapped_column(default=False, nullable=False)
    previous_password_hashes: Mapped[list] = mapped_column(JSON, default=list, nullable=False, doc="Recent hashes for reuse-prevention (password_history_size)")


class EmailVerificationTokenModel(Base, IdMixin):
    __tablename__ = "ip_email_verification_tokens"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PasswordResetTokenModel(Base, IdMixin):
    __tablename__ = "ip_password_reset_tokens"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_users.id"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    requested_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MagicLinkTokenModel(Base, IdMixin):
    __tablename__ = "ip_magic_link_tokens"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_users.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
