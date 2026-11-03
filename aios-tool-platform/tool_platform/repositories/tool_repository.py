from __future__ import annotations

from sqlalchemy import select

from tool_platform.models.tool import ToolModel, ToolVersionModel
from tool_platform.repositories.base import SQLAlchemyRepository


class ToolRepository(SQLAlchemyRepository[ToolModel]):
    model = ToolModel

    async def list_for_workspace(self, workspace_id: str, *, status: str | None = None, category: str | None = None) -> list[ToolModel]:
        stmt = select(ToolModel).where(ToolModel.workspace_id == workspace_id, ToolModel.is_deleted.is_(False))
        if status:
            stmt = stmt.where(ToolModel.status == status)
        if category:
            stmt = stmt.where(ToolModel.category == category)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_organization(self, organization_id: str) -> list[ToolModel]:
        stmt = select(ToolModel).where(ToolModel.organization_id == organization_id, ToolModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_slug(self, workspace_id: str, slug: str) -> ToolModel | None:
        stmt = select(ToolModel).where(
            ToolModel.workspace_id == workspace_id, ToolModel.slug == slug, ToolModel.is_deleted.is_(False)
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def search_by_tag(self, workspace_id: str, tag: str) -> list[ToolModel]:
        tools = await self.list_for_workspace(workspace_id)
        return [t for t in tools if tag in (t.tags or [])]

    async def search(self, workspace_id: str, query: str, *, limit: int = 50) -> list[ToolModel]:
        from sqlalchemy import func
        pattern = f"%{query.lower()}%"
        stmt = select(ToolModel).where(
            ToolModel.workspace_id == workspace_id, ToolModel.is_deleted.is_(False),
            func.lower(ToolModel.name).like(pattern),
        ).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class ToolVersionRepository(SQLAlchemyRepository[ToolVersionModel]):
    model = ToolVersionModel

    async def list_for_tool(self, tool_id: str) -> list[ToolVersionModel]:
        stmt = select(ToolVersionModel).where(ToolVersionModel.tool_id == tool_id).order_by(ToolVersionModel.version_number.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_latest_draft(self, tool_id: str) -> ToolVersionModel | None:
        stmt = select(ToolVersionModel).where(
            ToolVersionModel.tool_id == tool_id, ToolVersionModel.status == "draft",
        ).order_by(ToolVersionModel.version_number.desc())
        return (await self.session.execute(stmt)).scalars().first()

    async def get_max_version_number(self, tool_id: str) -> int:
        stmt = select(ToolVersionModel.version_number).where(ToolVersionModel.tool_id == tool_id).order_by(ToolVersionModel.version_number.desc())
        result = (await self.session.execute(stmt)).scalars().first()
        return result or 0
