from __future__ import annotations

from sqlalchemy import select

from developer_platform.models.cli import CliCommandLogModel, CliSessionModel
from developer_platform.repositories.base import SQLAlchemyRepository


class CliSessionRepository(SQLAlchemyRepository[CliSessionModel]):
    model = CliSessionModel

    async def get_by_token_hash(self, token_hash: str) -> CliSessionModel | None:
        stmt = select(CliSessionModel).where(CliSessionModel.token_hash == token_hash)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_developer(self, tenant_id: str, developer_id: str) -> list[CliSessionModel]:
        stmt = select(CliSessionModel).where(
            CliSessionModel.tenant_id == tenant_id, CliSessionModel.developer_id == developer_id
        )
        return list((await self.session.execute(stmt)).scalars().all())


class CliCommandLogRepository(SQLAlchemyRepository[CliCommandLogModel]):
    model = CliCommandLogModel

    async def list_for_session(self, tenant_id: str, session_id: str, *, limit: int = 200) -> list[CliCommandLogModel]:
        stmt = select(CliCommandLogModel).where(
            CliCommandLogModel.tenant_id == tenant_id, CliCommandLogModel.session_id == session_id
        ).order_by(CliCommandLogModel.executed_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
