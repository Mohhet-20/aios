"""Disaster Recovery: backups (guarded pending -> in_progress ->
completed/failed) and point-in-time snapshots per resource, reusable
recovery plans carrying an RPO/RTO commitment, guarded recovery
executions of a plan, and cross-region failover events. A recovery
can only be initiated against an active plan — the plan is the
reusable, tested definition; the execution is one guarded run of it,
the same "definition vs. run" split used by the Workflow Engine and
this platform's own CI/CD pipelines vs. pipeline runs."""
from __future__ import annotations

from datetime import timedelta, timezone

from infra_platform.config.settings import Settings, get_settings
from infra_platform.core.exceptions import (
    BackupFailedError,
    FailoverError,
    NotFoundError,
    RecoveryError,
    RecoveryPlanNotReadyError,
)
from infra_platform.domain.entities import Backup as BackupEntity
from infra_platform.domain.entities import RecoveryExecution as RecoveryExecutionEntity
from infra_platform.domain.enums import BackupStatus, FailoverStatus, RecoveryStatus
from infra_platform.models.recovery import (
    BackupModel,
    FailoverEventModel,
    RecoveryExecutionModel,
    RecoveryPlanModel,
    SnapshotModel,
)
from infra_platform.repositories.registry import RepositoryRegistry
from infra_platform.clock import utc_now

_FAILOVER_TRANSITIONS: dict[str, set[str]] = {
    FailoverStatus.INITIATED.value: {FailoverStatus.IN_PROGRESS.value, FailoverStatus.FAILED.value},
    FailoverStatus.IN_PROGRESS.value: {FailoverStatus.COMPLETED.value, FailoverStatus.FAILED.value},
    FailoverStatus.COMPLETED.value: set(),
    FailoverStatus.FAILED.value: set(),
}


def _to_backup_entity(model: BackupModel) -> BackupEntity:
    return BackupEntity(id=model.id, status=BackupStatus(model.status))


def _to_recovery_entity(model: RecoveryExecutionModel) -> RecoveryExecutionEntity:
    return RecoveryExecutionEntity(id=model.id, status=RecoveryStatus(model.status))


class BackupService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def create_backup(self, tenant_id: str, *, resource_type: str, resource_id: str) -> BackupModel:
        backup = BackupModel(tenant_id=tenant_id, resource_type=resource_type, resource_id=resource_id, status=BackupStatus.PENDING.value)
        return await self.repos.backups.add(backup)

    async def _get(self, tenant_id: str, backup_id: str) -> BackupModel:
        backup = await self.repos.backups.get(backup_id)
        if backup is None or backup.tenant_id != tenant_id:
            raise NotFoundError(f"Backup '{backup_id}' not found")
        return backup

    async def start_backup(self, tenant_id: str, backup_id: str) -> BackupModel:
        backup = await self._get(tenant_id, backup_id)
        entity = _to_backup_entity(backup)
        entity.start()
        backup.status = entity.status.value
        return await self.repos.backups.update(backup)

    async def complete_backup(self, tenant_id: str, backup_id: str, *, size_bytes: int | None = None, storage_uri: str | None = None) -> BackupModel:
        backup = await self._get(tenant_id, backup_id)
        entity = _to_backup_entity(backup)
        entity.complete()
        backup.status = entity.status.value
        backup.completed_at = entity.completed_at
        backup.size_bytes = size_bytes
        backup.storage_uri = storage_uri
        return await self.repos.backups.update(backup)

    async def fail_backup(self, tenant_id: str, backup_id: str) -> BackupModel:
        backup = await self._get(tenant_id, backup_id)
        entity = _to_backup_entity(backup)
        entity.fail()
        backup.status = entity.status.value
        backup.completed_at = entity.completed_at
        await self.repos.backups.update(backup)
        raise BackupFailedError(f"Backup '{backup_id}' failed")

    async def latest_for_resource(self, tenant_id: str, resource_type: str, resource_id: str) -> BackupModel | None:
        return await self.repos.backups.latest_for_resource(tenant_id, resource_type, resource_id)

    async def list_for_resource(self, tenant_id: str, resource_type: str, resource_id: str) -> list[BackupModel]:
        return await self.repos.backups.list_for_resource(tenant_id, resource_type, resource_id)

    async def prune_expired(self, tenant_id: str, resource_type: str, resource_id: str) -> int:
        """Deletes completed backups older than `backup_retention_days`."""
        cutoff = utc_now() - timedelta(days=self.settings.backup_retention_days)
        backups = await self.repos.backups.list_for_resource(tenant_id, resource_type, resource_id)
        pruned = 0
        for backup in backups:
            if backup.status != BackupStatus.COMPLETED.value or backup.completed_at is None:
                continue
            completed_at = backup.completed_at
            if completed_at.tzinfo is None:
                completed_at = completed_at.replace(tzinfo=timezone.utc)
            if completed_at < cutoff:
                await self.repos.backups.delete(backup)
                pruned += 1
        return pruned


class SnapshotService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def take_snapshot(
        self, tenant_id: str, *, resource_type: str, resource_id: str, backup_id: str | None = None, storage_uri: str | None = None
    ) -> SnapshotModel:
        snapshot = SnapshotModel(
            tenant_id=tenant_id, resource_type=resource_type, resource_id=resource_id, backup_id=backup_id, storage_uri=storage_uri
        )
        return await self.repos.snapshots.add(snapshot)

    async def list_for_resource(self, tenant_id: str, resource_type: str, resource_id: str) -> list[SnapshotModel]:
        return await self.repos.snapshots.list_for_resource(tenant_id, resource_type, resource_id)


class RecoveryPlanService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def create_plan(
        self, tenant_id: str, *, name: str, resource_type: str, rpo_minutes: int | None = None,
        rto_minutes: int | None = None, target_region: str | None = None,
    ) -> RecoveryPlanModel:
        existing = await self.repos.recovery_plans.get_by_name(tenant_id, name)
        if existing is not None:
            raise RecoveryError(f"Recovery plan '{name}' already exists")
        plan = RecoveryPlanModel(
            tenant_id=tenant_id, name=name, resource_type=resource_type,
            rpo_minutes=rpo_minutes if rpo_minutes is not None else self.settings.recovery_point_objective_minutes,
            rto_minutes=rto_minutes if rto_minutes is not None else self.settings.recovery_time_objective_minutes,
            target_region=target_region, is_active=True,
        )
        return await self.repos.recovery_plans.add(plan)

    async def _get(self, tenant_id: str, plan_id: str) -> RecoveryPlanModel:
        plan = await self.repos.recovery_plans.get(plan_id)
        if plan is None or plan.tenant_id != tenant_id:
            raise NotFoundError(f"RecoveryPlan '{plan_id}' not found")
        return plan

    async def deactivate(self, tenant_id: str, plan_id: str) -> RecoveryPlanModel:
        plan = await self._get(tenant_id, plan_id)
        plan.is_active = False
        return await self.repos.recovery_plans.update(plan)

    async def activate(self, tenant_id: str, plan_id: str) -> RecoveryPlanModel:
        plan = await self._get(tenant_id, plan_id)
        plan.is_active = True
        return await self.repos.recovery_plans.update(plan)

    async def list_active(self, tenant_id: str) -> list[RecoveryPlanModel]:
        return await self.repos.recovery_plans.list_active(tenant_id)


class RecoveryExecutionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def initiate_recovery(self, tenant_id: str, recovery_plan_id: str, *, notes: str | None = None) -> RecoveryExecutionModel:
        plan = await self.repos.recovery_plans.get(recovery_plan_id)
        if plan is None or plan.tenant_id != tenant_id:
            raise NotFoundError(f"RecoveryPlan '{recovery_plan_id}' not found")
        if not plan.is_active:
            raise RecoveryPlanNotReadyError(f"RecoveryPlan '{recovery_plan_id}' is not active")
        execution = RecoveryExecutionModel(
            tenant_id=tenant_id, recovery_plan_id=recovery_plan_id, status=RecoveryStatus.INITIATED.value, notes=notes
        )
        return await self.repos.recovery_executions.add(execution)

    async def _get(self, tenant_id: str, execution_id: str) -> RecoveryExecutionModel:
        execution = await self.repos.recovery_executions.get(execution_id)
        if execution is None or execution.tenant_id != tenant_id:
            raise NotFoundError(f"RecoveryExecution '{execution_id}' not found")
        return execution

    async def _transition(self, tenant_id: str, execution_id: str, action: str) -> RecoveryExecutionModel:
        execution = await self._get(tenant_id, execution_id)
        entity = _to_recovery_entity(execution)
        getattr(entity, action)()
        execution.status = entity.status.value
        execution.completed_at = entity.completed_at
        return await self.repos.recovery_executions.update(execution)

    async def start(self, tenant_id: str, execution_id: str) -> RecoveryExecutionModel:
        return await self._transition(tenant_id, execution_id, "start")

    async def complete(self, tenant_id: str, execution_id: str) -> RecoveryExecutionModel:
        return await self._transition(tenant_id, execution_id, "complete")

    async def fail(self, tenant_id: str, execution_id: str) -> RecoveryExecutionModel:
        return await self._transition(tenant_id, execution_id, "fail")

    async def list_for_plan(self, tenant_id: str, recovery_plan_id: str) -> list[RecoveryExecutionModel]:
        return await self.repos.recovery_executions.list_for_plan(tenant_id, recovery_plan_id)


class FailoverService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def initiate_failover(
        self, tenant_id: str, *, cluster_id: str | None = None, from_region: str, to_region: str
    ) -> FailoverEventModel:
        if from_region == to_region:
            raise FailoverError("from_region and to_region cannot be the same")
        event = FailoverEventModel(
            tenant_id=tenant_id, cluster_id=cluster_id, from_region=from_region, to_region=to_region,
            status=FailoverStatus.INITIATED.value,
        )
        return await self.repos.failover_events.add(event)

    async def _get(self, tenant_id: str, event_id: str) -> FailoverEventModel:
        event = await self.repos.failover_events.get(event_id)
        if event is None or event.tenant_id != tenant_id:
            raise NotFoundError(f"FailoverEvent '{event_id}' not found")
        return event

    async def _transition(self, tenant_id: str, event_id: str, target: str) -> FailoverEventModel:
        event = await self._get(tenant_id, event_id)
        allowed = _FAILOVER_TRANSITIONS.get(event.status, set())
        if target not in allowed:
            raise FailoverError(f"FailoverEvent '{event_id}' cannot transition from {event.status} to {target}")
        event.status = target
        if target in (FailoverStatus.COMPLETED.value, FailoverStatus.FAILED.value):
            event.completed_at = utc_now()
        return await self.repos.failover_events.update(event)

    async def mark_in_progress(self, tenant_id: str, event_id: str) -> FailoverEventModel:
        return await self._transition(tenant_id, event_id, FailoverStatus.IN_PROGRESS.value)

    async def complete(self, tenant_id: str, event_id: str) -> FailoverEventModel:
        return await self._transition(tenant_id, event_id, FailoverStatus.COMPLETED.value)

    async def fail(self, tenant_id: str, event_id: str) -> FailoverEventModel:
        return await self._transition(tenant_id, event_id, FailoverStatus.FAILED.value)

    async def list_for_cluster(self, tenant_id: str, cluster_id: str) -> list[FailoverEventModel]:
        return await self.repos.failover_events.list_for_cluster(tenant_id, cluster_id)
