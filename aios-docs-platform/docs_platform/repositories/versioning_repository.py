from __future__ import annotations

from sqlalchemy import select

from docs_platform.models.versioning import DeprecationNoticeModel, DocVersionModel, ReleaseNoteModel
from docs_platform.repositories.base import SQLAlchemyRepository


class DocVersionRepository(SQLAlchemyRepository[DocVersionModel]):
    model = DocVersionModel

    async def list_for_page(self, tenant_id: str, page_id: str) -> list[DocVersionModel]:
        stmt = select(DocVersionModel).where(
            DocVersionModel.tenant_id == tenant_id, DocVersionModel.page_id == page_id,
        ).order_by(DocVersionModel.version_number.asc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_version(self, tenant_id: str, page_id: str, version_number: int) -> DocVersionModel | None:
        stmt = select(DocVersionModel).where(
            DocVersionModel.tenant_id == tenant_id, DocVersionModel.page_id == page_id, DocVersionModel.version_number == version_number,
        )
        return (await self.session.execute(stmt)).scalars().first()


class ReleaseNoteRepository(SQLAlchemyRepository[ReleaseNoteModel]):
    model = ReleaseNoteModel

    async def list_for_tenant(self, tenant_id: str, *, version_label: str | None = None, limit: int = 100) -> list[ReleaseNoteModel]:
        stmt = select(ReleaseNoteModel).where(ReleaseNoteModel.tenant_id == tenant_id)
        if version_label:
            stmt = stmt.where(ReleaseNoteModel.version_label == version_label)
        stmt = stmt.order_by(ReleaseNoteModel.released_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class DeprecationNoticeRepository(SQLAlchemyRepository[DeprecationNoticeModel]):
    model = DeprecationNoticeModel

    async def list_for_tenant(self, tenant_id: str, *, limit: int = 100) -> list[DeprecationNoticeModel]:
        stmt = select(DeprecationNoticeModel).where(
            DeprecationNoticeModel.tenant_id == tenant_id,
        ).order_by(DeprecationNoticeModel.deprecated_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
