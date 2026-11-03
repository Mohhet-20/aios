"""InvitationModel: an email-addressed, token-based invitation to join
an organization (and optionally a specific workspace, with a role
pre-selected). `token_hash` follows the same never-store-raw pattern as
every other token model in this platform."""
from __future__ import annotations

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from identity_platform.database.base import Base, IdMixin, utcnow
from identity_platform.domain.enums import InvitationStatus


class InvitationModel(Base, IdMixin):
    __tablename__ = "ip_invitations"

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_organizations.id"), nullable=False, index=True)
    workspace_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ip_workspaces.id"), nullable=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    role_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ip_roles.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=InvitationStatus.PENDING.value, nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    invited_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_by_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    revoked_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
