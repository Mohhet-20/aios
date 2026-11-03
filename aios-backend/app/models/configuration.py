from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import AuditMixin, Base, IdMixin


class ConfigurationSettingModel(IdMixin, AuditMixin, Base):
    """Organization-scoped configuration overrides (feature flags,
    governance policy toggles) — the runtime counterpart to the static
    `app.config.settings.Settings` object, which only covers process-level
    config. See `ConfigurationService` for the merge precedence rule."""

    __tablename__ = "configuration_settings"

    organization_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
