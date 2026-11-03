"""Traffic Management schema: one generic `gw_traffic_rules` table
covering all ten routing strategies (weighted, canary, blue-green,
header, path, region, priority, mirror, split, failover) via a
`rule_type` discriminator and a free-form `config` JSON blob shaped
per type — the same "generic table + typed config" pattern the
Developer Platform's package registry used for its five package
types, avoiding ten near-identical tables for what is really one
concept (route -> destination selection logic) with different
selection criteria."""
from __future__ import annotations

from sqlalchemy import JSON, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from gateway_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class TrafficRuleModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "gw_traffic_rules"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    route_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="active", index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
