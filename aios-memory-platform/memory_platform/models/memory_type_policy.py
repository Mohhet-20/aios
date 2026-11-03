"""Data-driven memory-type registry — the 16 memory types are rows here,
not Python classes, exactly like the Agent Platform's AgentTypeModel. A
new memory type (or a policy change to an existing one, e.g. a longer
retention window for LONG_TERM) is a row insert/update, not a code
change."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from memory_platform.database.base import AuditMixin, Base, IdMixin


class MemoryTypePolicyModel(Base, IdMixin, AuditMixin):
    __tablename__ = "mem_memory_type_policies"

    key: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True, doc="Matches domain.enums.MemoryType value")
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    default_retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True, doc="Null = retained indefinitely")
    default_importance: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    decay_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, doc="Importance lost per day since last access")
    is_persistent: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, doc="False = TTL-bound working/session memory")
    summarize_after_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, doc="Trigger compression once content exceeds this many tokens")
    max_entries_per_scope: Mapped[int | None] = mapped_column(Integer, nullable=True, doc="Null = unbounded")
    default_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
