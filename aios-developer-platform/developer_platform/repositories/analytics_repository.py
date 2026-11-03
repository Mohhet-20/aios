from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select

from developer_platform.models.analytics import UsageEventModel
from developer_platform.repositories.base import SQLAlchemyRepository


class UsageEventRepository(SQLAlchemyRepository[UsageEventModel]):
    model = UsageEventModel

    async def list_recent(self, tenant_id: str, *, event_type: str | None = None, limit: int = 200) -> list[UsageEventModel]:
        stmt = select(UsageEventModel).where(UsageEventModel.tenant_id == tenant_id)
        if event_type:
            stmt = stmt.where(UsageEventModel.event_type == event_type)
        stmt = stmt.order_by(UsageEventModel.recorded_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_by_type(self, tenant_id: str) -> dict[str, int]:
        from sqlalchemy import func

        stmt = select(UsageEventModel.event_type, func.count()).where(UsageEventModel.tenant_id == tenant_id).group_by(
            UsageEventModel.event_type
        )
        rows = (await self.session.execute(stmt)).all()
        return {t: c for t, c in rows}

    async def delete_older_than(self, tenant_id: str, cutoff: datetime) -> int:
        stmt = delete(UsageEventModel).where(
            UsageEventModel.tenant_id == tenant_id, UsageEventModel.recorded_at < cutoff
        ).execution_options(synchronize_session=False)
        result = await self.session.execute(stmt)
        return result.rowcount or 0
