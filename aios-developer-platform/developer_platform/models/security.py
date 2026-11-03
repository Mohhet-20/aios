"""Developer Platform Security schema: ordered RBAC role bindings
(viewer < operator < admin) and secret references — this platform
never stores a raw webhook signing secret, plugin secret, or API
credential directly; `SecretReferenceModel.material_ref` is an opaque
pointer, the same "own the pointer, not the data" boundary the
Security Platform's encryption module disclosed for its own key
material."""
from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from developer_platform.database.base import AuditMixin, Base, IdMixin


class DeveloperRoleBindingModel(IdMixin, AuditMixin, Base):
    __tablename__ = "dev_role_bindings"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    principal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    scope: Mapped[str | None] = mapped_column(String(100), nullable=True)


class SecretReferenceModel(IdMixin, AuditMixin, Base):
    __tablename__ = "dev_secret_references"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    reference_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    material_ref: Mapped[str] = mapped_column(String(200), nullable=False)
