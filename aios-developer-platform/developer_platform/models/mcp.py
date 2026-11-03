"""MCP Integration schema: registered MCP servers (transport +
connection status), sessions opened against a server (client
identity, guarded active -> expired/closed lifecycle), and discovery
caches for the resources/tools/prompts a connected server exposes.

DISCLOSED SCOPE BOUNDARY: this platform is the control plane that
tracks MCP servers, sessions, and discovered capabilities — it does
not itself speak the wire protocol over a real stdio/HTTP/SSE
transport. `McpServerModel.endpoint_ref` is the seam where a real
transport adapter would plug in, the same disclosed-gap posture as
the Infrastructure Platform's Kubernetes module."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from developer_platform.database.base import AuditMixin, Base, IdMixin, utcnow


class McpServerModel(IdMixin, AuditMixin, Base):
    __tablename__ = "dev_mcp_servers"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    transport: Mapped[str] = mapped_column(String(10), nullable=False, default="stdio")
    endpoint_ref: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="registered", index=True)
    protocol_version: Mapped[str] = mapped_column(String(20), nullable=False, default="2024-11-05")


class McpSessionModel(IdMixin, Base):
    __tablename__ = "dev_mcp_sessions"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    mcp_server_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    client_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(15), nullable=False, default="active", index=True)
    permissions: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class McpResourceModel(IdMixin, Base):
    __tablename__ = "dev_mcp_resources"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    mcp_server_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    uri: Mapped[str] = mapped_column(String(500), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True)


class McpToolModel(IdMixin, Base):
    __tablename__ = "dev_mcp_tools"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    mcp_server_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    input_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)


class McpPromptModel(IdMixin, Base):
    __tablename__ = "dev_mcp_prompts"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    mcp_server_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    arguments_schema: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
