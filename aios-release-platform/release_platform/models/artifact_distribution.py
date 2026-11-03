"""Artifact Management & Enterprise Distribution schema: build
artifacts across 11 declared types, distribution channels (registries,
repositories, offline bundles), and the publish record linking an
artifact to a channel."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from release_platform.database.base import AuditMixin, Base, IdMixin


class ArtifactModel(IdMixin, AuditMixin, Base):
    __tablename__ = "rel_artifacts"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    release_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True)
    storage_uri: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    signed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class DistributionChannelModel(IdMixin, AuditMixin, Base):
    __tablename__ = "rel_distribution_channels"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    channel_type: Mapped[str] = mapped_column(String(25), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    endpoint_uri: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class DistributionEntryModel(IdMixin, Base):
    __tablename__ = "rel_distribution_entries"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    artifact_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    channel_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="published")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
