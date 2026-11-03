"""ObservabilityEventModel: one ingested execution event from any
upstream AIOS platform (prompt/agent/workflow/tool/memory) — the raw
material every timeline, latency chart, and failure/retry stat in this
platform is computed from. Genuinely-measured fields only; a field this
platform has no real signal for (e.g. CPU usage from a platform that
doesn't report it) is left null rather than estimated."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from eval_platform.database.base import Base, IdMixin, utcnow


class ObservabilityEventModel(Base, IdMixin):
    __tablename__ = "ep_observability_events"

    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source_platform: Mapped[str] = mapped_column(String(40), nullable=False, doc='e.g. "prompt_platform", "agent_platform", "workflow_engine", "tool_platform", "memory_platform"')
    source_execution_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    queue_time_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    retry_count: Mapped[int] = mapped_column(default=0, nullable=False)

    token_usage: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="{input_tokens, output_tokens, total_tokens} when genuinely reported")
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    resource_usage: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="{cpu_seconds, peak_memory_mb, network_bytes, storage_bytes} — only ever populated from a genuine measurement")

    payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="Free-form event-specific detail (model used, tool name, memory scope, ...)")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
