from __future__ import annotations

from sqlalchemy import select

from eval_platform.models.hallucination import HallucinationCheckModel
from eval_platform.repositories.base import SQLAlchemyRepository


class HallucinationCheckRepository(SQLAlchemyRepository[HallucinationCheckModel]):
    model = HallucinationCheckModel

    async def list_for_subject(self, subject_type: str, subject_id: str) -> list[HallucinationCheckModel]:
        stmt = select(HallucinationCheckModel).where(HallucinationCheckModel.subject_type == subject_type, HallucinationCheckModel.subject_id == subject_id)
        return list((await self.session.execute(stmt)).scalars().all())

    async def list_for_workspace(self, workspace_id: str, *, grounded: bool | None = None, limit: int = 200) -> list[HallucinationCheckModel]:
        stmt = select(HallucinationCheckModel).where(HallucinationCheckModel.workspace_id == workspace_id)
        if grounded is not None:
            stmt = stmt.where(HallucinationCheckModel.grounded.is_(grounded))
        stmt = stmt.order_by(HallucinationCheckModel.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
