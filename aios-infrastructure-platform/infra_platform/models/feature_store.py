"""Feature Store schema: feature groups (an entity-keyed collection,
e.g. all features keyed by `user_id`), features within a group
(versioned, with an online/offline serving flag inherited from the
group), and validation rules attached to a feature (not-null, range,
regex — checked by `feature_store/validation.py`)."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from infra_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class FeatureGroupModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "infra_feature_groups"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    entity_key: Mapped[str] = mapped_column(String(100), nullable=False)
    online_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    offline_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class FeatureModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_features"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    feature_group_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    value_type: Mapped[str] = mapped_column(String(10), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)


class FeatureValidationRuleModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_feature_validation_rules"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    feature_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(30), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
