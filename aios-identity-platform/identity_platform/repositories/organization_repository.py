from __future__ import annotations

from sqlalchemy import select

from identity_platform.models.organization import DepartmentModel, OrganizationModel
from identity_platform.repositories.base import SQLAlchemyRepository


class OrganizationRepository(SQLAlchemyRepository[OrganizationModel]):
    model = OrganizationModel

    async def get_by_slug(self, slug: str) -> OrganizationModel | None:
        stmt = select(OrganizationModel).where(OrganizationModel.slug == slug, OrganizationModel.is_deleted.is_(False))
        return (await self.session.execute(stmt)).scalars().first()


class DepartmentRepository(SQLAlchemyRepository[DepartmentModel]):
    model = DepartmentModel

    async def list_for_organization(self, organization_id: str) -> list[DepartmentModel]:
        stmt = select(DepartmentModel).where(DepartmentModel.organization_id == organization_id)
        return list((await self.session.execute(stmt)).scalars().all())
