"""SDK Platform schema: a per-language compatibility matrix entry
mapping an SDK major version to the range of platform API versions it
supports. SDK package artifacts themselves live in the generic
Package Registry (`registry.py`, `package_type="sdk"`) — this table
is purely the compatibility declaration layer on top of that."""
from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from developer_platform.database.base import AuditMixin, Base, IdMixin


class SdkCompatibilityEntryModel(IdMixin, AuditMixin, Base):
    __tablename__ = "dev_sdk_compatibility_entries"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    language: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    sdk_major_version: Mapped[int] = mapped_column(Integer, nullable=False)
    min_api_version: Mapped[str] = mapped_column(String(20), nullable=False)
    max_api_version: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
