from __future__ import annotations

from sqlalchemy import select

from developer_platform.models.portal import PortalContentModel, SandboxEnvironmentModel
from developer_platform.repositories.base import SQLAlchemyRepository


class PortalContentRepository(SQLAlchemyRepository[PortalContentModel]):
    model = PortalContentModel

    async def get_by_slug(self, tenant_id: str, content_type: str, slug: str) -> PortalContentModel | None:
        stmt = select(PortalContentModel).where(
            PortalContentModel.tenant_id == tenant_id, PortalContentModel.content_type == content_type, PortalContentModel.slug == slug
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_by_type(self, tenant_id: str, content_type: str) -> list[PortalContentModel]:
        stmt = select(PortalContentModel).where(
            PortalContentModel.tenant_id == tenant_id, PortalContentModel.content_type == content_type
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_published(self, tenant_id: str) -> list[PortalContentModel]:
        stmt = select(PortalContentModel).where(
            PortalContentModel.tenant_id == tenant_id, PortalContentModel.status == "published"
        )
        return list((await self.session.execute(stmt)).scalars().all())


class SandboxEnvironmentRepository(SQLAlchemyRepository[SandboxEnvironmentModel]):
    model = SandboxEnvironmentModel

    async def list_for_developer(self, tenant_id: str, developer_id: str) -> list[SandboxEnvironmentModel]:
        stmt = select(SandboxEnvironmentModel).where(
            SandboxEnvironmentModel.tenant_id == tenant_id, SandboxEnvironmentModel.developer_id == developer_id
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_active_for_developer(self, tenant_id: str, developer_id: str) -> list[SandboxEnvironmentModel]:
        stmt = select(SandboxEnvironmentModel).where(
            SandboxEnvironmentModel.tenant_id == tenant_id, SandboxEnvironmentModel.developer_id == developer_id,
            SandboxEnvironmentModel.status.in_(["provisioning", "running"]),
        )
        return list((await self.session.execute(stmt)).scalars().all())
