"""Golden test cases and the runs/results of executing them against a
prompt version."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from prompt_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow
from prompt_platform.domain.enums import RunStatus, TestRunType


class GoldenTestCaseModel(Base, IdMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "golden_test_cases"

    prompt_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompts.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    input_variables: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    assertions: Mapped[list] = mapped_column(JSON, default=list, nullable=False, doc="[{type, value}]")
    max_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class TestRunModel(Base, IdMixin, AuditMixin):
    __tablename__ = "test_runs"

    prompt_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompts.id"), nullable=False, index=True)
    version_id: Mapped[str] = mapped_column(String(36), ForeignKey("prompt_versions.id"), nullable=False, index=True)
    run_type: Mapped[str] = mapped_column(String(20), default=TestRunType.SINGLE.value, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=RunStatus.PENDING.value, nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(36), nullable=False)
    started_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at = mapped_column(DateTime(timezone=True), nullable=True)
    summary: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="{total, passed, failed, pass_rate}")


class TestResultModel(Base, IdMixin):
    __tablename__ = "test_results"

    test_run_id: Mapped[str] = mapped_column(String(36), ForeignKey("test_runs.id"), nullable=False, index=True)
    golden_test_case_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("golden_test_cases.id"), nullable=True)
    rendered_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(120), nullable=True)
    provider_used: Mapped[str | None] = mapped_column(String(60), nullable=True)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    failure_reasons: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
