"""Secrets & encryption schema. `SecretModel` is the guarded lifecycle
record; `SecretVersionModel` holds the actual ciphertext (never
plaintext) with the encryption key reference used to produce it, so
rotating the master key doesn't require decrypting-and-re-encrypting
every version retroactively — only new versions use the new key.
`EncryptionKeyModel.material_ref` is deliberately NOT the raw key
material — see `encryption/`'s module docstring for the disclosed KMS
boundary."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from security_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, VersionedMixin, utcnow


class SecretModel(IdMixin, AuditMixin, SoftDeleteMixin, VersionedMixin, Base):
    __tablename__ = "sec_secrets"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    secret_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    current_version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SecretVersionModel(IdMixin, Base):
    __tablename__ = "sec_secret_versions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    secret_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    ciphertext: Mapped[str] = mapped_column(String(4000), nullable=False)
    nonce: Mapped[str] = mapped_column(String(100), nullable=False)
    encryption_key_id: Mapped[str] = mapped_column(String(36), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class SecretAccessPolicyModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "sec_secret_access_policies"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    secret_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    principal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    can_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    can_rotate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SecretAccessLogModel(IdMixin, Base):
    __tablename__ = "sec_secret_access_log"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    secret_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    principal_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class EncryptionKeyModel(IdMixin, AuditMixin, Base):
    __tablename__ = "sec_encryption_keys"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    key_type: Mapped[str] = mapped_column(String(30), nullable=False, default="fernet")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    material_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
