"""Package Registry schema: a single generic store for every package
type the platform distributes — SDK packages, plugin packages,
workflow templates, prompt templates, agent templates — one
`RegistryPackageModel` per named package (unique per name+type),
versioned beneath it with a guarded draft -> published -> deprecated
lifecycle and an opaque `storage_uri` pointer, following the same
"own the pointer, not the data" posture used across every AIOS
platform's artifact-shaped stores."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from developer_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class RegistryPackageModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "dev_registry_packages"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    package_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class RegistryPackageVersionModel(IdMixin, AuditMixin, Base):
    __tablename__ = "dev_registry_package_versions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    package_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    language: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="draft", index=True)
    storage_uri: Mapped[str | None] = mapped_column(String(500), nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(100), nullable=True)
    dependencies: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
