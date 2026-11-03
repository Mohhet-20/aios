"""Feature Flag Platform schema: a flag with a base scope/rollout
percentage, plus per-target overrides (organization, workspace, user,
experiment) that take precedence over the base flag state — the same
"specific overrides a general default" shape used for visibility and
RBAC scoping in sibling AIOS platforms."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from release_platform.database.base import AuditMixin, Base, IdMixin


class FeatureFlagModel(IdMixin, AuditMixin, Base):
    __tablename__ = "rel_feature_flags"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    scope: Mapped[str] = mapped_column(String(15), nullable=False, default="global", index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rollout_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_kill_switch: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False, default="")


class FeatureFlagOverrideModel(IdMixin, AuditMixin, Base):
    __tablename__ = "rel_feature_flag_overrides"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    flag_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    target_ref: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    config_overrides: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
