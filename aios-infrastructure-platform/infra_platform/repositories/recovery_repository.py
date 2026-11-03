from __future__ import annotations

from sqlalchemy import select

from infra_platform.models.recovery import BackupModel, FailoverEventModel, RecoveryExecutionModel, RecoveryPlanModel, SnapshotModel
from infra_platform.repositories.base import SQLAlchemyRepository


class BackupRepository(SQLAlchemyRepository[BackupModel]):
    model = BackupModel

    async def list_for_resource(self, tenant_id: str, resource_type: str, resource_id: str) -> list[BackupModel]:
        stmt = select(BackupModel).where(
            BackupModel.tenant_id == tenant_id, BackupModel.resource_type == resource_type, BackupModel.resource_id == resource_id
        ).order_by(BackupModel.started_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())

    async def latest_for_resource(self, tenant_id: str, resource_type: str, resource_id: str) -> BackupModel | None:
        results = await self.list_for_resource(tenant_id, resource_type, resource_id)
        return results[0] if results else None


class SnapshotRepository(SQLAlchemyRepository[SnapshotModel]):
    model = SnapshotModel

    async def list_for_resource(self, tenant_id: str, resource_type: str, resource_id: str) -> list[SnapshotModel]:
        stmt = select(SnapshotModel).where(
            SnapshotModel.tenant_id == tenant_id, SnapshotModel.resource_type == resource_type, SnapshotModel.resource_id == resource_id
        ).order_by(SnapshotModel.taken_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())


class RecoveryPlanRepository(SQLAlchemyRepository[RecoveryPlanModel]):
    model = RecoveryPlanModel

    async def get_by_name(self, tenant_id: str, name: str) -> RecoveryPlanModel | None:
        stmt = select(RecoveryPlanModel).where(RecoveryPlanModel.tenant_id == tenant_id, RecoveryPlanModel.name == name, RecoveryPlanModel.is_deleted.is_(False))
        return (await self.session.execute(stmt)).scalars().first()

    async def list_active(self, tenant_id: str) -> list[RecoveryPlanModel]:
        stmt = select(RecoveryPlanModel).where(RecoveryPlanModel.tenant_id == tenant_id, RecoveryPlanModel.is_deleted.is_(False), RecoveryPlanModel.is_active.is_(True))
        return list((await self.session.execute(stmt)).scalars().all())


class RecoveryExecutionRepository(SQLAlchemyRepository[RecoveryExecutionModel]):
    model = RecoveryExecutionModel

    async def list_for_plan(self, tenant_id: str, recovery_plan_id: str) -> list[RecoveryExecutionModel]:
        stmt = select(RecoveryExecutionModel).where(
            RecoveryExecutionModel.tenant_id == tenant_id, RecoveryExecutionModel.recovery_plan_id == recovery_plan_id
        ).order_by(RecoveryExecutionModel.started_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())


class FailoverEventRepository(SQLAlchemyRepository[FailoverEventModel]):
    model = FailoverEventModel

    async def list_for_cluster(self, tenant_id: str, cluster_id: str) -> list[FailoverEventModel]:
        stmt = select(FailoverEventModel).where(
            FailoverEventModel.tenant_id == tenant_id, FailoverEventModel.cluster_id == cluster_id
        ).order_by(FailoverEventModel.initiated_at.desc())
        return list((await self.session.execute(stmt)).scalars().all())
