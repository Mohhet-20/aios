from __future__ import annotations

from sqlalchemy import select

from developer_platform.models.mcp import McpPromptModel, McpResourceModel, McpServerModel, McpSessionModel, McpToolModel
from developer_platform.repositories.base import SQLAlchemyRepository


class McpServerRepository(SQLAlchemyRepository[McpServerModel]):
    model = McpServerModel

    async def get_by_name(self, tenant_id: str, name: str) -> McpServerModel | None:
        stmt = select(McpServerModel).where(McpServerModel.tenant_id == tenant_id, McpServerModel.name == name)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str) -> list[McpServerModel]:
        stmt = select(McpServerModel).where(McpServerModel.tenant_id == tenant_id)
        return list((await self.session.execute(stmt)).scalars().all())


class McpSessionRepository(SQLAlchemyRepository[McpSessionModel]):
    model = McpSessionModel

    async def list_for_server(self, tenant_id: str, mcp_server_id: str) -> list[McpSessionModel]:
        stmt = select(McpSessionModel).where(
            McpSessionModel.tenant_id == tenant_id, McpSessionModel.mcp_server_id == mcp_server_id
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_active(self, tenant_id: str) -> list[McpSessionModel]:
        stmt = select(McpSessionModel).where(McpSessionModel.tenant_id == tenant_id, McpSessionModel.status == "active")
        return list((await self.session.execute(stmt)).scalars().all())


class McpResourceRepository(SQLAlchemyRepository[McpResourceModel]):
    model = McpResourceModel

    async def list_for_server(self, tenant_id: str, mcp_server_id: str) -> list[McpResourceModel]:
        stmt = select(McpResourceModel).where(
            McpResourceModel.tenant_id == tenant_id, McpResourceModel.mcp_server_id == mcp_server_id
        )
        return list((await self.session.execute(stmt)).scalars().all())


class McpToolRepository(SQLAlchemyRepository[McpToolModel]):
    model = McpToolModel

    async def list_for_server(self, tenant_id: str, mcp_server_id: str) -> list[McpToolModel]:
        stmt = select(McpToolModel).where(McpToolModel.tenant_id == tenant_id, McpToolModel.mcp_server_id == mcp_server_id)
        return list((await self.session.execute(stmt)).scalars().all())


class McpPromptRepository(SQLAlchemyRepository[McpPromptModel]):
    model = McpPromptModel

    async def list_for_server(self, tenant_id: str, mcp_server_id: str) -> list[McpPromptModel]:
        stmt = select(McpPromptModel).where(McpPromptModel.tenant_id == tenant_id, McpPromptModel.mcp_server_id == mcp_server_id)
        return list((await self.session.execute(stmt)).scalars().all())
