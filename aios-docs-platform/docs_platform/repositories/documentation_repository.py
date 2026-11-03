from __future__ import annotations

from sqlalchemy import select

from docs_platform.models.documentation import DocPageModel, DocSpaceModel
from docs_platform.repositories.base import SQLAlchemyRepository


class DocSpaceRepository(SQLAlchemyRepository[DocSpaceModel]):
    model = DocSpaceModel

    async def get_by_key(self, tenant_id: str, key: str) -> DocSpaceModel | None:
        stmt = select(DocSpaceModel).where(
            DocSpaceModel.tenant_id == tenant_id, DocSpaceModel.key == key, DocSpaceModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str, *, doc_type: str | None = None) -> list[DocSpaceModel]:
        stmt = select(DocSpaceModel).where(DocSpaceModel.tenant_id == tenant_id, DocSpaceModel.is_deleted.is_(False))
        if doc_type:
            stmt = stmt.where(DocSpaceModel.doc_type == doc_type)
        return list((await self.session.execute(stmt)).scalars().all())


class DocPageRepository(SQLAlchemyRepository[DocPageModel]):
    model = DocPageModel

    async def get_by_slug(self, tenant_id: str, space_id: str, slug: str) -> DocPageModel | None:
        stmt = select(DocPageModel).where(
            DocPageModel.tenant_id == tenant_id, DocPageModel.space_id == space_id,
            DocPageModel.slug == slug, DocPageModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_space(self, tenant_id: str, space_id: str, *, status: str | None = None) -> list[DocPageModel]:
        stmt = select(DocPageModel).where(
            DocPageModel.tenant_id == tenant_id, DocPageModel.space_id == space_id, DocPageModel.is_deleted.is_(False),
        )
        if status:
            stmt = stmt.where(DocPageModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_tenant(self, tenant_id: str, *, doc_type: str | None = None, status: str | None = None) -> list[DocPageModel]:
        stmt = select(DocPageModel).where(DocPageModel.tenant_id == tenant_id, DocPageModel.is_deleted.is_(False))
        if doc_type:
            stmt = stmt.where(DocPageModel.doc_type == doc_type)
        if status:
            stmt = stmt.where(DocPageModel.status == status)
        return list((await self.session.execute(stmt)).scalars().all())
