"""Experiment tracking schema: experiments group runs; runs carry
status + timing; metrics and parameters are logged as append-only
key/value rows against a run (metrics support multi-step logging via
`step`, parameters are logged once per key per run)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infra_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow


class ExperimentModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "infra_experiments"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    owner_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class ExperimentRunModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_experiment_runs"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    experiment_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    run_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running", index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)


class RunMetricModel(IdMixin, Base):
    __tablename__ = "infra_run_metrics"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    step: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    logged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RunParamModel(IdMixin, Base):
    __tablename__ = "infra_run_params"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    run_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(200), nullable=False)
    value: Mapped[str] = mapped_column(String(2000), nullable=False)
