from __future__ import annotations

from sqlalchemy import select

from docs_platform.models.architecture import DiagramModel, TechStackEntryModel
from docs_platform.repositories.base import SQLAlchemyRepository


class DiagramRepository(SQLAlchemyRepository[DiagramModel]):
    model = DiagramModel

    async def list_for_tenant(self, tenant_id: str, *, diagram_type: str | None = None) -> list[DiagramModel]:
        stmt = select(DiagramModel).where(DiagramModel.tenant_id == tenant_id, DiagramModel.is_deleted.is_(False))
        if diagram_type:
            stmt = stmt.where(DiagramModel.diagram_type == diagram_type)
        return list((await self.session.execute(stmt)).scalars().all())


class TechStackEntryRepository(SQLAlchemyRepository[TechStackEntryModel]):
    model = TechStackEntryModel

    async def list_for_tenant(self, tenant_id: str, *, category: str | None = None) -> list[TechStackEntryModel]:
        stmt = select(TechStackEntryModel).where(TechStackEntryModel.tenant_id == tenant_id)
        if category:
            stmt = stmt.where(TechStackEntryModel.category == category)
        return list((await self.session.execute(stmt)).scalars().all())
