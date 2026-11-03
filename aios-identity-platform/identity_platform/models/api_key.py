"""ApiKeyModel: a scoped, hashed-at-rest credential owned by either a
user or a `ServiceAccountModel` (machine identity). `key_prefix` is the
short, non-secret visible portion (`sk_live_ab12...`) shown in a list
UI so an owner can recognize a key without ever seeing the secret
again post-issuance — the same "never returns a decrypted secret"
discipline the Tool Platform's credential vault uses.
`WebhookSecretModel` is the HMAC signing secret for outbound webhook
payload verification."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from identity_platform.database.base import AuditMixin, Base, IdMixin, utcnow
from identity_platform.domain.enums import ApiKeyStatus, ServiceAccountStatus


class ApiKeyModel(Base, IdMixin):
    __tablename__ = "ip_api_keys"

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_organizations.id"), nullable=False, index=True)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ip_workspaces.id"), nullable=True)
    owner_type: Mapped[str] = mapped_column(String(20), nullable=False, doc="'user' or 'service_account'")
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    scopes: Mapped[list] = mapped_column(JSON, default=list, nullable=False, doc="Permission keys this key is limited to")
    status: Mapped[str] = mapped_column(String(20), default=ApiKeyStatus.ACTIVE.value, nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(String(200), nullable=True)


class ServiceAccountModel(Base, IdMixin, AuditMixin):
    __tablename__ = "ip_service_accounts"

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=ServiceAccountStatus.ACTIVE.value, nullable=False, index=True)


class WebhookSecretModel(Base, IdMixin):
    __tablename__ = "ip_webhook_secrets"

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_organizations.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    secret_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    rotated_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
