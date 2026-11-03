from __future__ import annotations

from sqlalchemy import select

from collaboration_platform.domain.enums import PresenceStatus
from collaboration_platform.models.presence import ConflictRecordModel, EditSessionModel, PresenceSessionModel
from collaboration_platform.repositories.base import SQLAlchemyRepository


class PresenceSessionRepository(SQLAlchemyRepository[PresenceSessionModel]):
    model = PresenceSessionModel

    async def list_active_for_asset(self, asset_id: str) -> list[PresenceSessionModel]:
        stmt = select(PresenceSessionModel).where(
            PresenceSessionModel.asset_id == asset_id,
            PresenceSessionModel.status != PresenceStatus.DISCONNECTED.value,
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_connection_id(self, connection_id: str) -> PresenceSessionModel | None:
        stmt = select(PresenceSessionModel).where(PresenceSessionModel.connection_id == connection_id)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_stale(self, *, cutoff) -> list[PresenceSessionModel]:
        stmt = select(PresenceSessionModel).where(
            PresenceSessionModel.status != PresenceStatus.DISCONNECTED.value,
            PresenceSessionModel.last_heartbeat_at < cutoff,
        )
        return list((await self.session.execute(stmt)).scalars().all())


class EditSessionRepository(SQLAlchemyRepository[EditSessionModel]):
    model = EditSessionModel

    async def list_active_for_asset(self, asset_id: str) -> list[EditSessionModel]:
        stmt = select(EditSessionModel).where(EditSessionModel.asset_id == asset_id, EditSessionModel.ended_at.is_(None))
        return list((await self.session.execute(stmt)).scalars().all())


class ConflictRecordRepository(SQLAlchemyRepository[ConflictRecordModel]):
    model = ConflictRecordModel

    async def list_for_asset(self, asset_id: str) -> list[ConflictRecordModel]:
        stmt = select(ConflictRecordModel).where(ConflictRecordModel.asset_id == asset_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_unresolved(self) -> list[ConflictRecordModel]:
        stmt = select(ConflictRecordModel).where(ConflictRecordModel.resolved_at.is_(None))
        return list((await self.session.execute(stmt)).scalars().all())
