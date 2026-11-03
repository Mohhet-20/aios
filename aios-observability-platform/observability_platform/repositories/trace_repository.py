from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select

from observability_platform.models.tracing import SpanModel, TraceModel
from observability_platform.repositories.base import SQLAlchemyRepository


class TraceRepository(SQLAlchemyRepository[TraceModel]):
    model = TraceModel

    async def get_by_trace_id(self, tenant_id: str, trace_id: str) -> TraceModel | None:
        stmt = select(TraceModel).where(TraceModel.tenant_id == tenant_id, TraceModel.trace_id == trace_id)
        return (await self.session.execute(stmt)).scalars().first()

    async def list_recent(self, tenant_id: str, *, service_name: str | None = None, limit: int = 100) -> list[TraceModel]:
        stmt = select(TraceModel).where(TraceModel.tenant_id == tenant_id)
        if service_name:
            stmt = stmt.where(TraceModel.root_service == service_name)
        stmt = stmt.order_by(TraceModel.started_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_older_than(self, tenant_id: str, cutoff: datetime) -> int:
        stmt = delete(TraceModel).where(
            TraceModel.tenant_id == tenant_id, TraceModel.started_at < cutoff
        ).execution_options(synchronize_session=False)
        result = await self.session.execute(stmt)
        return result.rowcount or 0


class SpanRepository(SQLAlchemyRepository[SpanModel]):
    model = SpanModel

    async def list_for_trace(self, tenant_id: str, trace_id: str) -> list[SpanModel]:
        stmt = (
            select(SpanModel)
            .where(SpanModel.tenant_id == tenant_id, SpanModel.trace_id == trace_id)
            .order_by(SpanModel.start_time.asc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def count_for_trace(self, tenant_id: str, trace_id: str) -> int:
        from sqlalchemy import func

        stmt = select(func.count()).select_from(SpanModel).where(
            SpanModel.tenant_id == tenant_id, SpanModel.trace_id == trace_id
        )
        return (await self.session.execute(stmt)).scalar_one()

    async def list_recent_for_tenant(
        self, tenant_id: str, *, span_kind: str | None = None, limit: int = 5000
    ) -> list[SpanModel]:
        """Lists spans directly by tenant, independent of whether their
        parent trace has been finalized into a `TraceModel` summary row
        yet — analysis code (slow-query detection, per-span-kind
        performance) needs to see spans as soon as they're ingested, not
        only after a trace's summary row exists."""
        stmt = select(SpanModel).where(SpanModel.tenant_id == tenant_id)
        if span_kind:
            stmt = stmt.where(SpanModel.span_kind == span_kind)
        stmt = stmt.order_by(SpanModel.start_time.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def delete_older_than(self, tenant_id: str, cutoff: datetime) -> int:
        stmt = delete(SpanModel).where(
            SpanModel.tenant_id == tenant_id, SpanModel.start_time < cutoff
        ).execution_options(synchronize_session=False)
        result = await self.session.execute(stmt)
        return result.rowcount or 0
