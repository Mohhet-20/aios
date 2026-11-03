from __future__ import annotations

from sqlalchemy import select

from tool_platform.models.credential import CredentialModel, ToolCredentialBindingModel
from tool_platform.repositories.base import SQLAlchemyRepository


class CredentialRepository(SQLAlchemyRepository[CredentialModel]):
    model = CredentialModel

    async def list_for_workspace(self, workspace_id: str) -> list[CredentialModel]:
        stmt = select(CredentialModel).where(CredentialModel.workspace_id == workspace_id, CredentialModel.is_deleted.is_(False))
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_active_expiring_before(self, *, as_of) -> list[CredentialModel]:
        stmt = select(CredentialModel).where(
            CredentialModel.status.in_(["active", "rotating"]),
            CredentialModel.expires_at.is_not(None),
            CredentialModel.expires_at <= as_of,
        )
        return list((await self.session.execute(stmt)).scalars().all())


class ToolCredentialBindingRepository(SQLAlchemyRepository[ToolCredentialBindingModel]):
    model = ToolCredentialBindingModel

    async def get_default_for_tool(self, tool_id: str, workspace_id: str) -> ToolCredentialBindingModel | None:
        stmt = select(ToolCredentialBindingModel).where(
            ToolCredentialBindingModel.tool_id == tool_id,
            ToolCredentialBindingModel.workspace_id == workspace_id,
            ToolCredentialBindingModel.is_default.is_(True),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tool(self, tool_id: str) -> list[ToolCredentialBindingModel]:
        stmt = select(ToolCredentialBindingModel).where(ToolCredentialBindingModel.tool_id == tool_id)
        return list((await self.session.execute(stmt)).scalars().all())
