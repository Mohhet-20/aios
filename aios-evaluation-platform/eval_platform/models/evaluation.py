"""EvaluationModel: the top-level identity record for a reusable
evaluation (what's being measured, its category, ownership). The
versioned *contract* — which dataset it runs against, which metrics it
computes, its scoring config and pass threshold — lives in
`EvaluationVersionModel`, the same Tool/ToolVersion-style split every
prior AIOS platform uses so an in-flight `EvaluationRun` keeps scoring
against the exact configuration it started with even if the evaluation
gets edited and republished underneath it."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from eval_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow
from eval_platform.domain.enums import EvaluationStatus, EvaluationVersionStatus


class EvaluationModel(Base, IdMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "ep_evaluations"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("ep_workspaces.id"), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=EvaluationStatus.DRAFT.value, nullable=False, index=True)
    current_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ep_evaluation_versions.id"), nullable=True)
    eval_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class EvaluationVersionModel(Base, IdMixin):
    __tablename__ = "ep_evaluation_versions"

    evaluation_id: Mapped[str] = mapped_column(String(36), ForeignKey("ep_evaluations.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=EvaluationVersionStatus.DRAFT.value, nullable=False)
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    dataset_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ep_datasets.id"), nullable=True)
    metric_keys: Mapped[list] = mapped_column(JSON, default=list, nullable=False, doc="Keys into the metric registry this evaluation computes")
    scoring_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="Per-metric weights/config used to roll up an overall score")
    pass_threshold: Mapped[float | None] = mapped_column(nullable=True, doc="Overall score at/above which an item/run is considered passing")
    target_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc='What is being evaluated, e.g. {"type": "prompt", "ref_id": "..."} or {"type": "agent", ...}')

    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
