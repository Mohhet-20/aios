"""DatasetModel: identity for a reusable evaluation dataset (golden,
synthetic, human-annotated, regression, production-sample, or an
evaluation-suite grouping). `DatasetVersionModel` is the immutable
snapshot of items an `EvaluationVersionModel` actually binds to —
appending new items always creates or updates a draft version, so a
published `EvaluationRun` history stays reproducible against the exact
item set it ran against. `lineage_parent_dataset_id` tracks provenance
when a dataset is derived from another (e.g. a regression dataset built
from filtered production samples)."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from eval_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow
from eval_platform.domain.enums import DatasetStatus


class DatasetModel(Base, IdMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "ep_datasets"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("ep_workspaces.id"), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    dataset_type: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=DatasetStatus.DRAFT.value, nullable=False, index=True)
    current_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ep_dataset_versions.id"), nullable=True)
    lineage_parent_dataset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ep_datasets.id"), nullable=True)
    shared_with_workspace_ids: Mapped[list] = mapped_column(JSON, default=list, nullable=False, doc="Other workspaces (same org) this dataset is explicitly shared with")
    dataset_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class DatasetVersionModel(Base, IdMixin):
    __tablename__ = "ep_dataset_versions"

    dataset_id: Mapped[str] = mapped_column(String(36), ForeignKey("ep_datasets.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=DatasetStatus.DRAFT.value, nullable=False)
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    item_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class DatasetItemModel(Base, IdMixin):
    __tablename__ = "ep_dataset_items"

    dataset_version_id: Mapped[str] = mapped_column(String(36), ForeignKey("ep_dataset_versions.id"), nullable=False, index=True)
    input_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    expected_output: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    item_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="e.g. annotator id, source, difficulty tag")
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
