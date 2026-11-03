"""HallucinationCheckModel: one grounding/fact-verification pass over a
piece of generated text against a source context — fact verification,
citation validation, unsupported-claims detection, and a confidence
score, all in one record. Not tied exclusively to an evaluation run:
`subject_type`/`subject_id` let this be called standalone (e.g. from
Observability on a live production response) or as part of an
evaluation item's scoring."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from eval_platform.database.base import Base, IdMixin, utcnow


class HallucinationCheckModel(Base, IdMixin):
    __tablename__ = "ep_hallucination_checks"

    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(40), nullable=False, doc='e.g. "evaluation_item", "observability_event", "adhoc"')
    subject_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    source_context: Mapped[str] = mapped_column(Text, nullable=False)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)

    grounded: Mapped[bool] = mapped_column(Boolean, nullable=False)
    groundedness_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    unsupported_claims: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    citations_checked: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    consistency_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    method: Mapped[str] = mapped_column(String(40), default="lexical_overlap", nullable=False, doc="Which grounding method produced this result — swappable for an external verifier later")
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
