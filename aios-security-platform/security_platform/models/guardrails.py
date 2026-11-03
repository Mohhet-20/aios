"""Guardrail schema: configurable rules, an append-only evaluation log
(every guardrail check, allowed or not — needed for false-positive
tuning and compliance evidence), and violations (a guarded lifecycle
record opened when an evaluation's action was FLAG or BLOCK, distinct
from the evaluation log the same way an Alert is distinct from a
metric point in the Observability Platform)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from security_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class GuardrailRuleModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "sec_guardrail_rules"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    action: Mapped[str] = mapped_column(String(10), nullable=False, default="flag")
    risk_threshold: Mapped[float] = mapped_column(Float, nullable=False, default=0.6)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class GuardrailEvaluationModel(IdMixin, Base):
    __tablename__ = "sec_guardrail_evaluations"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    input_excerpt: Mapped[str] = mapped_column(String(2000), nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    action_taken: Mapped[str] = mapped_column(String(10), nullable=False, default="allow")
    matched_rule_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    matched_signals: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    context: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)


class GuardrailViolationModel(IdMixin, AuditMixin, Base):
    __tablename__ = "sec_guardrail_violations"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    evaluation_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(10), nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open", index=True)
    resource_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolution_notes: Mapped[str | None] = mapped_column(String(2000), nullable=True)
