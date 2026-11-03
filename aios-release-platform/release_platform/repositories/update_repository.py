from __future__ import annotations

from sqlalchemy import select

from release_platform.models.update import UpdateJobModel
from release_platform.repositories.base import SQLAlchemyRepository


class UpdateJobRepository(SQLAlchemyRepository[UpdateJobModel]):
    model = UpdateJobModel

    async def list_for_target(self, tenant_id: str, target_ref: str, *, limit: int = 100) -> list[UpdateJobModel]:
        stmt = select(UpdateJobModel).where(
            UpdateJobModel.tenant_id == tenant_id, UpdateJobModel.target_ref == target_ref,
        ).order_by(UpdateJobModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
