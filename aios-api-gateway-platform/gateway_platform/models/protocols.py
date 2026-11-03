"""Protocol Translation schema: a config row per (source route,
translation pair) describing how to transform a request/response
across protocols — payload/schema/auth transformation rules live in
the free-form `config` JSON blob, keeping the table generic across
all three supported pairs (REST<->GraphQL, REST<->WebSocket,
REST<->Event Stream) plus version translation."""
from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from gateway_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class ProtocolTranslationConfigModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "gw_protocol_translations"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    route_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    translation_pair: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="active", index=True)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
