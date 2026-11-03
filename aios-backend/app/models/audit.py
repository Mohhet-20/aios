from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, IdMixin, utcnow


class AuditLogModel(IdMixin, Base):
    """Audit logs are append-only: no `AuditMixin`/`SoftDeleteMixin` here on
    purpose, since a mutable or deletable audit trail defeats its own
    purpose. Repositories expose `add()` and read queries only — there is no
    `update()`/`delete()` path wired to this table anywhere in the service
    layer."""

    __tablename__ = "audit_logs"

    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    actor: Mapped[str] = mapped_column(String(255), nullable=False)
    action: Mapped[str] = mapped_column(String(255), nullable=False)
    resource: Mapped[str] = mapped_column(String(255), nullable=False)
    ip_address: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="success", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
