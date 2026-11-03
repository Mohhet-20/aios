"""LLM cost-intelligence routing: policies scoping which model tiers a
tenant/workspace/user-tier may use, and a log of individual routing
decisions (for analytics and for the auto-optimization engine to mine)."""
from __future__ import annotations

from sqlalchemy import JSON, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from perf_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class RoutingPolicyModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "perf_routing_policies"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    scope_type: Mapped[str] = mapped_column(String(32), nullable=False)  # organization | workspace | user
    scope_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    allowed_tiers: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    max_cost_per_request_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    default_tier: Mapped[str] = mapped_column(String(32), nullable=False, default="medium")


class RoutingDecisionModel(IdMixin, AuditMixin, Base):
    __tablename__ = "perf_routing_decisions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    task_complexity: Mapped[str] = mapped_column(String(32), nullable=False)
    chosen_tier: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    user_tier: Mapped[str] = mapped_column(String(32), nullable=False)
    latency_budget_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_cost_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    reasoning: Mapped[str] = mapped_column(String, nullable=False, default="")
