"""NodeDefinitionModel: the data-driven node-type registry — the same
"extensibility via data, not code" lesson every other AIOS platform's
type registry used (`AgentTypeModel`, `MemoryTypePolicyModel`). Adding a
31st node type, or tuning an existing one's default timeout/retry
policy, is a row insert/update, not a new Python class — though the
*handler* logic for a genuinely new node type is still real code (see
`node_library/`); this table is the policy/metadata layer above it."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from workflow_platform.database.base import Base, IdMixin


class NodeDefinitionModel(Base, IdMixin):
    __tablename__ = "wf_node_definitions"

    key: Mapped[str] = mapped_column(String(40), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False, doc="control_flow | ai | integration | human | data | custom")
    input_schema: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_schema: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    default_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    default_timeout_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)
    default_max_retries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    default_retry_backoff_seconds: Mapped[float] = mapped_column(Float, default=2.0, nullable=False)
    is_compensable: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, doc="Whether this node type supports rollback/compensation logic")
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
