from __future__ import annotations

from sqlalchemy import select

from quality_platform.models.quality_gates import CoverageSnapshotModel, QualityGateCheckResultModel, QualityGateModel
from quality_platform.repositories.base import SQLAlchemyRepository


class QualityGateRepository(SQLAlchemyRepository[QualityGateModel]):
    model = QualityGateModel

    async def get_for_release(self, tenant_id: str, release_ref: str, name: str) -> QualityGateModel | None:
        stmt = select(QualityGateModel).where(
            QualityGateModel.tenant_id == tenant_id, QualityGateModel.release_ref == release_ref,
            QualityGateModel.name == name, QualityGateModel.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalars().first()

    async def list_for_tenant(self, tenant_id: str, *, release_ref: str | None = None) -> list[QualityGateModel]:
        stmt = select(QualityGateModel).where(
            QualityGateModel.tenant_id == tenant_id, QualityGateModel.is_deleted.is_(False),
        )
        if release_ref:
            stmt = stmt.where(QualityGateModel.release_ref == release_ref)
        return list((await self.session.execute(stmt)).scalars().all())


class QualityGateCheckResultRepository(SQLAlchemyRepository[QualityGateCheckResultModel]):
    model = QualityGateCheckResultModel

    async def list_for_gate(self, tenant_id: str, quality_gate_id: str) -> list[QualityGateCheckResultModel]:
        stmt = select(QualityGateCheckResultModel).where(
            QualityGateCheckResultModel.tenant_id == tenant_id, QualityGateCheckResultModel.quality_gate_id == quality_gate_id,
        )
        return list((await self.session.execute(stmt)).scalars().all())


class CoverageSnapshotRepository(SQLAlchemyRepository[CoverageSnapshotModel]):
    model = CoverageSnapshotModel

    async def list_for_subject(
        self, tenant_id: str, subject_ref: str, *, coverage_type: str | None = None, limit: int = 200,
    ) -> list[CoverageSnapshotModel]:
        stmt = select(CoverageSnapshotModel).where(
            CoverageSnapshotModel.tenant_id == tenant_id, CoverageSnapshotModel.subject_ref == subject_ref,
        )
        if coverage_type:
            stmt = stmt.where(CoverageSnapshotModel.coverage_type == coverage_type)
        stmt = stmt.order_by(CoverageSnapshotModel.recorded_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())
