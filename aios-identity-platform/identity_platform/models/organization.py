"""OrganizationModel: the top of the tenancy hierarchy and the
isolation boundary every workspace/team/project/user-membership/API-key
hangs off of. `branding`/`settings`/`compliance_metadata` are flexible
JSON so tenant customization never requires a schema migration.
`DepartmentModel` supports both departments and business units
(`unit_type`) with a self-referential parent for a real org chart."""
from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from identity_platform.database.base import AuditMixin, Base, IdMixin, SoftDeleteMixin
from identity_platform.domain.enums import OrganizationStatus, TenantTier


class OrganizationModel(Base, IdMixin, AuditMixin, SoftDeleteMixin):
    __tablename__ = "ip_organizations"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(220), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default=OrganizationStatus.ACTIVE.value, nullable=False, index=True)
    tenant_tier: Mapped[str] = mapped_column(String(20), default=TenantTier.FREE.value, nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    billing_email: Mapped[str | None] = mapped_column(String(320), nullable=True)

    settings: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="Tenant configuration/policies toggles")
    branding: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="logo_url/primary_color/custom_domain")
    compliance_metadata: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False, doc="data_residency/compliance_frameworks/retention overrides")

    seat_quota: Mapped[int] = mapped_column(Integer, default=25, nullable=False)
    workspace_quota: Mapped[int] = mapped_column(Integer, default=10, nullable=False)


class DepartmentModel(Base, IdMixin, AuditMixin):
    __tablename__ = "ip_departments"

    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("ip_organizations.id"), nullable=False, index=True)
    unit_type: Mapped[str] = mapped_column(String(20), nullable=False, doc="'department' or 'business_unit'")
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    parent_department_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("ip_departments.id"), nullable=True)
