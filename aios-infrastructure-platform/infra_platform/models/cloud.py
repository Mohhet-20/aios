"""Multi-cloud schema: cloud accounts (a credential/subscription
reference per provider — never raw credentials, see `cloud/`'s module
docstring) and cloud resources, a generic pointer to anything
provisioned in a real cloud (mirroring the Security Platform's
`GovernanceAssetModel` "own the pointer, not the data" pattern)."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from infra_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class CloudAccountModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "infra_cloud_accounts"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    account_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class CloudResourceModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_cloud_resources"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    cloud_account_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    region: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    external_id: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    tags: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
