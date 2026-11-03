"""ExternalIdentityModel: links a platform `UserModel` to an identity
at a federated provider (Google/GitHub/Azure AD/generic OIDC/SAML) —
one user can link multiple providers. `raw_profile` keeps whatever the
provider's userinfo/attribute response contained, for debugging and
for claims a future feature might want without a schema change."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from identity_platform.database.base import Base, IdMixin, utcnow


class ExternalIdentityModel(Base, IdMixin):
    __tablename__ = "ip_external_identities"
    __table_args__ = (UniqueConstraint("provider_key", "provider_user_id", name="uq_provider_identity"),)

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_users.id"), nullable=False, index=True)
    provider_key: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    provider_user_id: Mapped[str] = mapped_column(String(200), nullable=False)
    provider_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    raw_profile: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    linked_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
