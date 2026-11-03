from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select

from observability_platform.models.logs import LogEntryModel
from observability_platform.repositories.base import SQLAlchemyRepository


class LogEntryRepository(SQLAlchemyRepository[LogEntryModel]):
    model = LogEntryModel

    async def search(
        self,
        tenant_id: str,
        *,
        level: str | None = None,
        service_name: str | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        user_id: str | None = None,
        text_query: str | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 200,
    ) -> list[LogEntryModel]:
        stmt = select(LogEntryModel).where(LogEntryModel.tenant_id == tenant_id)
        if level:
            stmt = stmt.where(LogEntryModel.level == level)
        if service_name:
            stmt = stmt.where(LogEntryModel.service_name == service_name)
        if correlation_id:
            stmt = stmt.where(LogEntryModel.correlation_id == correlation_id)
        if trace_id:
            stmt = stmt.where(LogEntryModel.trace_id == trace_id)
        if user_id:
            stmt = stmt.where(LogEntryModel.user_id == user_id)
        if start_time:
            stmt = stmt.where(LogEntryModel.event_time >= start_time)
        if end_time:
            stmt = stmt.where(LogEntryModel.event_time <= end_time)
        if text_query:
            stmt = stmt.where(LogEntryModel.message.ilike(f"%{text_query}%"))
        stmt = stmt.order_by(LogEntryModel.event_time.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_by_level(
        self, tenant_id: str, *, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> dict[str, int]:
        stmt = select(LogEntryModel.level, func.count()).where(LogEntryModel.tenant_id == tenant_id)
        if start_time:
            stmt = stmt.where(LogEntryModel.event_time >= start_time)
        if end_time:
            stmt = stmt.where(LogEntryModel.event_time <= end_time)
        stmt = stmt.group_by(LogEntryModel.level)
        rows = (await self.session.execute(stmt)).all()
        return {level: count for level, count in rows}

    async def count_total(self, tenant_id: str, *, start_time: datetime | None = None, end_time: datetime | None = None) -> int:
        stmt = select(func.count()).select_from(LogEntryModel).where(LogEntryModel.tenant_id == tenant_id)
        if start_time:
            stmt = stmt.where(LogEntryModel.event_time >= start_time)
        if end_time:
            stmt = stmt.where(LogEntryModel.event_time <= end_time)
        return (await self.session.execute(stmt)).scalar_one()

    async def delete_older_than(self, tenant_id: str, cutoff: datetime) -> int:
        """Hard-deletes expired log rows in one statement — retention
        sweeps operate on high-volume append-only data, so there's no
        soft-delete flag to flip, just a real bulk delete."""
        stmt = delete(LogEntryModel).where(
            LogEntryModel.tenant_id == tenant_id, LogEntryModel.event_time < cutoff
        ).execution_options(synchronize_session=False)
        result = await self.session.execute(stmt)
        return result.rowcount or 0
