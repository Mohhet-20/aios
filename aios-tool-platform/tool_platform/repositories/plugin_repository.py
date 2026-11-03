from __future__ import annotations

from sqlalchemy import select

from tool_platform.models.plugin import PluginDependencyModel, PluginInstallationModel, PluginModel
from tool_platform.repositories.base import SQLAlchemyRepository


class PluginRepository(SQLAlchemyRepository[PluginModel]):
    model = PluginModel

    async def get_by_slug(self, slug: str) -> PluginModel | None:
        stmt = select(PluginModel).where(PluginModel.slug == slug, PluginModel.is_deleted.is_(False))
        return (await self.session.execute(stmt)).scalars().first()

    async def search(self, *, category: str | None = None, tag: str | None = None, query: str | None = None) -> list[PluginModel]:
        stmt = select(PluginModel).where(PluginModel.is_deleted.is_(False), PluginModel.status == "published")
        if category:
            stmt = stmt.where(PluginModel.category == category)
        results = list((await self.session.execute(stmt)).scalars().all())
        if tag:
            results = [p for p in results if tag in (p.tags or [])]
        if query:
            q = query.lower()
            results = [p for p in results if q in p.name.lower() or q in (p.description or "").lower()]
        return results


class PluginDependencyRepository(SQLAlchemyRepository[PluginDependencyModel]):
    model = PluginDependencyModel

    async def list_for_plugin(self, plugin_id: str) -> list[PluginDependencyModel]:
        stmt = select(PluginDependencyModel).where(PluginDependencyModel.plugin_id == plugin_id)
        return list((await self.session.execute(stmt)).scalars().all())


class PluginInstallationRepository(SQLAlchemyRepository[PluginInstallationModel]):
    model = PluginInstallationModel

    async def list_for_workspace(self, workspace_id: str) -> list[PluginInstallationModel]:
        stmt = select(PluginInstallationModel).where(PluginInstallationModel.workspace_id == workspace_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_for_workspace(self, workspace_id: str, plugin_id: str) -> PluginInstallationModel | None:
        stmt = select(PluginInstallationModel).where(
            PluginInstallationModel.workspace_id == workspace_id, PluginInstallationModel.plugin_id == plugin_id,
        )
        return (await self.session.execute(stmt)).scalars().first()
