"""Cache platform tables: individual cache entries (any of the 11
declared layers) and rolling per-layer hit/miss counters."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from perf_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class CacheEntryModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "perf_cache_entries"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    layer: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    value: Mapped[str] = mapped_column(String, nullable=False)
    ttl_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    hit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class CacheStatModel(IdMixin, AuditMixin, Base):
    """Rolling per-(tenant, layer) counters — cheap to read for a
    dashboard without scanning every cache_entries row."""
    __tablename__ = "perf_cache_stats"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    layer: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    hits: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    misses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evictions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    hit_rate_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
