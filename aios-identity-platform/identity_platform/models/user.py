"""UserModel: platform-wide identity, not scoped to one organization —
a user can belong to multiple organizations via `OrganizationMembershipModel`.
`failed_login_count`/`locked_until` back real account-lockout/brute-force
protection (see `security/lockout_service.py`); they're mutated by the
authentication flow itself, not a side table."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from identity_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin
from identity_platform.domain.enums import UserStatus


class UserModel(Base, IdMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "ip_users"

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    email_verified_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default=UserStatus.PENDING_VERIFICATION.value, nullable=False, index=True)

    display_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", nullable=False)
    locale: Mapped[str] = mapped_column(String(16), default="en-US", nullable=False)
    notification_preferences: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    primary_organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    last_login_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    locked_until: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
