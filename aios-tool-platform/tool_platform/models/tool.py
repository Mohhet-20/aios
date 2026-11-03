"""ToolModel: the top-level tool record — identity, ownership,
categorization, health, and the pointer to whichever `ToolVersionModel`
is currently active. `ToolVersionModel` is the versioned contract
(input/output schema, validation rules, capabilities, configuration,
auth requirement) — editing a tool creates or updates a DRAFT version
rather than mutating a published one in place, exactly like the
Workflow Engine's WorkflowModel/WorkflowVersionModel split, so an
in-flight execution keeps running against the exact schema/config it
started with."""
from __future__ import annotations

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from tool_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin, utcnow
from tool_platform.domain.enums import ToolHealth, ToolStatus, ToolVersionStatus


class ToolModel(Base, IdMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "tp_tools"

    workspace_id: Mapped[str] = mapped_column(String(36), ForeignKey("tp_workspaces.id"), nullable=False, index=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    tags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=ToolStatus.DRAFT.value, nullable=False, index=True)
    health: Mapped[str] = mapped_column(String(20), default=ToolHealth.UNKNOWN.value, nullable=False)
    health_checked_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_version_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("tp_tool_versions.id"), nullable=True)
    tool_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class ToolVersionModel(Base, IdMixin):
    __tablename__ = "tp_tool_versions"

    tool_id: Mapped[str] = mapped_column(String(36), ForeignKey("tp_tools.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default=ToolVersionStatus.DRAFT.value, nullable=False)
    change_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    capabilities: Mapped[list] = mapped_column(JSON, default=list, nullable=False, doc="Free-form capability tags, e.g. ['network_access', 'read_file']")
    input_schema: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="JSON Schema the tool call's input_data must satisfy")
    output_schema: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="JSON Schema the tool call's output_data must satisfy")
    validation_rules: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="Extra rules beyond JSON Schema, e.g. max input size")
    configuration: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="Default config merged under per-call overrides (base_url, connector-specific settings, ...)")
    auth_requirement: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc='{"type": "api_key"|"oauth2"|..., "scopes": [...]} or {} for no auth')
    sensitivity_level: Mapped[str] = mapped_column(String(20), default="normal", nullable=False)

    default_timeout_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    default_max_retries: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    default_retry_backoff_seconds: Mapped[float] = mapped_column(Float, default=1.5, nullable=False)

    connector_key: Mapped[str | None] = mapped_column(
        String(80), nullable=True, index=True,
        doc="Key into the in-process connector registry (tool_registry/registry.py) that actually "
            "executes this tool type — e.g. 'http_client', 'github'. None for pure-custom/plugin tools "
            "that bring their own handler through the plugin system.",
    )

    created_by: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
