"""Artifact Management schema: a generic store for models, datasets,
embeddings, prompt templates, agent configs, workflow templates,
evaluation reports, training outputs, and deployment packages — one
`ArtifactModel` per named artifact, versioned beneath it. This is
intentionally the same shape for every artifact type since what
varies is metadata, not structure."""
from __future__ import annotations

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infra_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class ArtifactModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "infra_artifacts"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class ArtifactVersionModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_artifact_versions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    artifact_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(500), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    checksum: Mapped[str | None] = mapped_column(String(100), nullable=True)
    artifact_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
