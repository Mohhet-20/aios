"""Infra security & governance schema: network policies (namespace/
cluster-scoped ingress/egress rules), runtime policies (seccomp/
apparmor/resource-limit style constraints), and infra RBAC role
bindings (the ordered viewer/operator/admin grammar defined in
`domain/enums.py`)."""
from __future__ import annotations

from sqlalchemy import JSON, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from infra_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin


class NetworkPolicyModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "infra_network_policies"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    cluster_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    namespace: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    rules: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RuntimePolicyModel(IdMixin, AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "infra_runtime_policies"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    policy_type: Mapped[str] = mapped_column(String(30), nullable=False)
    rules: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class InfraRoleBindingModel(IdMixin, AuditMixin, Base):
    __tablename__ = "infra_role_bindings"

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    principal_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    scope: Mapped[str | None] = mapped_column(String(100), nullable=True)
