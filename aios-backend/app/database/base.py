"""Declarative base and reusable mixins.

`AuditMixin`, `SoftDeleteMixin`, and `VersionedMixin` are composed into every
ORM model in `app/models/` so audit fields, soft deletes, and optimistic
locking are implemented exactly once and cannot drift between tables.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.clock import utc_now


def utcnow() -> datetime:
    return utc_now()


def new_uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    """Root declarative base shared by every ORM model."""

    pass


class IdMixin:
    """UUID primary key, generated application-side (portable across SQLite
    and Postgres, unlike auto-increment integers, and safe to assign before
    a row is flushed — useful for emitting domain events with a stable ID)."""

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)


class AuditMixin:
    """created_at / updated_at / created_by / updated_by on every entity —
    the "Audit Fields" requirement from the persistence layer design."""

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class SoftDeleteMixin:
    """Rows are never physically deleted — `is_deleted`/`deleted_at` are set
    instead. Repositories filter these out by default; audit/compliance
    tooling can still read them directly when required."""

    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VersionedMixin:
    """Optimistic locking via a monotonically increasing `version` column.
    Checked and incremented explicitly in `BaseRepository.update()` (compare
    the caller's expected version against the current row, bump on success,
    raise `ConcurrentModificationError` on mismatch) rather than relying on
    SQLAlchemy's built-in `version_id_col` mapper argument, which is awkward
    to compose with mixins — this keeps the mechanism simple, explicit, and
    identical across every entity that opts into it."""

    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
