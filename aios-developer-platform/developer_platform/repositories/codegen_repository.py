from __future__ import annotations

from sqlalchemy import select

from developer_platform.models.codegen import CodeGenArtifactModel, CodeGenJobModel
from developer_platform.repositories.base import SQLAlchemyRepository


class CodeGenJobRepository(SQLAlchemyRepository[CodeGenJobModel]):
    model = CodeGenJobModel

    async def list_for_tenant(self, tenant_id: str, *, limit: int = 200) -> list[CodeGenJobModel]:
        stmt = select(CodeGenJobModel).where(CodeGenJobModel.tenant_id == tenant_id).order_by(
            CodeGenJobModel.created_at.desc()
        ).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())


class CodeGenArtifactRepository(SQLAlchemyRepository[CodeGenArtifactModel]):
    model = CodeGenArtifactModel

    async def list_for_job(self, tenant_id: str, job_id: str) -> list[CodeGenArtifactModel]:
        stmt = select(CodeGenArtifactModel).where(
            CodeGenArtifactModel.tenant_id == tenant_id, CodeGenArtifactModel.job_id == job_id
        )
        return list((await self.session.execute(stmt)).scalars().all())
