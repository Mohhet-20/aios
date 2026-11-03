from __future__ import annotations

from sqlalchemy import select

from identity_platform.models.workspace import WorkspaceModel
from identity_platform.repositories.base import SQLAlchemyRepository


class WorkspaceRepository(SQLAlchemyRepository[WorkspaceModel]):
    model = WorkspaceModel

    async def list_for_organization(self, organization_id: str) -> list[WorkspaceModel]:
        stmt = select(WorkspaceModel).where(WorkspaceModel.organization_id == organization_id, WorkspaceModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_slug(self, organization_id: str, slug: str) -> WorkspaceModel | None:
        stmt = select(WorkspaceModel).where(
            WorkspaceModel.organization_id == organization_id, WorkspaceModel.slug == slug, WorkspaceModel.is_deleted.is_(False)
        )
        return (await self.session.execute(stmt)).scalars().first()
