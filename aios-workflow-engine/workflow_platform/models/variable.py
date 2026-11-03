"""VariableModel: persistent, longer-lived state — workspace-wide or
global variables that outlive any one execution — orthogonal to
`ExecutionModel.context_variables`, which is ephemeral per-run state.
`is_secret` flags a variable for encryption-at-rest via the Security
layer rather than storing it as plain JSON."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from workflow_platform.database.base import Base, IdMixin, utcnow


class VariableModel(Base, IdMixin):
    __tablename__ = "wf_variables"
    __table_args__ = (UniqueConstraint("scope_type", "scope_id", "key", name="uq_wf_variable_scope_key"),)

    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True, doc="workflow | execution | workspace | global")
    scope_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[dict] = mapped_column(JSON, nullable=False, doc="Always JSON-wrapped as {'v': <value>} so any JSON type — including a bare string or number — round-trips")
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
