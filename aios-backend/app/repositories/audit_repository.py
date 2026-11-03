from sqlalchemy import select

from app.models.audit import AuditLogModel
from app.repositories.base import SQLAlchemyRepository


class AuditRepository(SQLAlchemyRepository[AuditLogModel]):
    """Append-only by convention: `update()`/`delete()` are inherited but no
    service ever calls them for this repository — enforced by code review /
    the absence of any `AuditService.update()` method, not by a DB-level
    trigger, which would be the natural next hardening step in production."""

    model = AuditLogModel

    async def list_recent(self, organization_id: str, limit: int = 100) -> list[AuditLogModel]:
        result = await self.session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.organization_id == organization_id)
            .order_by(AuditLogModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
