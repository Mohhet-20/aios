"""Tests for Disaster Recovery: backup lifecycle (success and failure
paths), retention pruning, snapshots, recovery plan CRUD, execution
gated on an active plan, and failover event transitions."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from infra_platform.config.settings import Settings
from infra_platform.core.exceptions import (
    BackupFailedError,
    FailoverError,
    InvalidTransitionError,
    NotFoundError,
    RecoveryError,
    RecoveryPlanNotReadyError,
)
from infra_platform.recovery.recovery_service import (
    BackupService,
    FailoverService,
    RecoveryExecutionService,
    RecoveryPlanService,
    SnapshotService,
)

TENANT = "tenant-recovery"


@pytest.mark.asyncio
async def test_backup_happy_path(repos):
    service = BackupService(repos)
    backup = await service.create_backup(TENANT, resource_type="cluster", resource_id="cluster-1")
    assert backup.status == "pending"

    backup = await service.start_backup(TENANT, backup.id)
    assert backup.status == "in_progress"

    backup = await service.complete_backup(TENANT, backup.id, size_bytes=1024, storage_uri="s3://backups/cluster-1.tar")
    assert backup.status == "completed"
    assert backup.completed_at is not None

    latest = await service.latest_for_resource(TENANT, "cluster", "cluster-1")
    assert latest.id == backup.id


@pytest.mark.asyncio
async def test_backup_failure_raises(repos):
    service = BackupService(repos)
    backup = await service.create_backup(TENANT, resource_type="database", resource_id="db-1")
    await service.start_backup(TENANT, backup.id)

    with pytest.raises(BackupFailedError):
        await service.fail_backup(TENANT, backup.id)

    refreshed = await service._get(TENANT, backup.id)
    assert refreshed.status == "failed"

    with pytest.raises(InvalidTransitionError):
        await service.start_backup(TENANT, backup.id)


@pytest.mark.asyncio
async def test_prune_expired_backups(repos):
    service = BackupService(repos, settings=Settings(backup_retention_days=30))
    old_backup = await service.create_backup(TENANT, resource_type="volume", resource_id="vol-1")
    await service.start_backup(TENANT, old_backup.id)
    old_backup = await service.complete_backup(TENANT, old_backup.id)
    # backdate completed_at beyond retention window directly on the model
    old_backup.completed_at = datetime.now(timezone.utc) - timedelta(days=45)
    await repos.backups.update(old_backup)

    recent_backup = await service.create_backup(TENANT, resource_type="volume", resource_id="vol-1")
    await service.start_backup(TENANT, recent_backup.id)
    await service.complete_backup(TENANT, recent_backup.id)

    pruned = await service.prune_expired(TENANT, "volume", "vol-1")
    assert pruned == 1
    remaining = await service.list_for_resource(TENANT, "volume", "vol-1")
    assert len(remaining) == 1
    assert remaining[0].id == recent_backup.id


@pytest.mark.asyncio
async def test_snapshot_recording(repos):
    service = SnapshotService(repos)
    await service.take_snapshot(TENANT, resource_type="database", resource_id="db-2", storage_uri="s3://snaps/db-2.snap")
    await service.take_snapshot(TENANT, resource_type="database", resource_id="db-2", storage_uri="s3://snaps/db-2-b.snap")

    snaps = await service.list_for_resource(TENANT, "database", "db-2")
    assert len(snaps) == 2


@pytest.mark.asyncio
async def test_recovery_plan_defaults_and_duplicate(repos):
    service = RecoveryPlanService(repos, settings=Settings(recovery_point_objective_minutes=15, recovery_time_objective_minutes=60))
    plan = await service.create_plan(TENANT, name="db-dr-plan", resource_type="database")
    assert plan.rpo_minutes == 15
    assert plan.rto_minutes == 60

    with pytest.raises(RecoveryError):
        await service.create_plan(TENANT, name="db-dr-plan", resource_type="database")


@pytest.mark.asyncio
async def test_recovery_execution_requires_active_plan(repos):
    plan_service = RecoveryPlanService(repos)
    execution_service = RecoveryExecutionService(repos)
    plan = await plan_service.create_plan(TENANT, name="cluster-dr-plan", resource_type="cluster")
    await plan_service.deactivate(TENANT, plan.id)

    with pytest.raises(RecoveryPlanNotReadyError):
        await execution_service.initiate_recovery(TENANT, plan.id)

    await plan_service.activate(TENANT, plan.id)
    execution = await execution_service.initiate_recovery(TENANT, plan.id)
    assert execution.status == "initiated"

    execution = await execution_service.start(TENANT, execution.id)
    assert execution.status == "in_progress"

    execution = await execution_service.complete(TENANT, execution.id)
    assert execution.status == "completed"
    assert execution.completed_at is not None


@pytest.mark.asyncio
async def test_failover_lifecycle(repos):
    service = FailoverService(repos)
    with pytest.raises(FailoverError):
        await service.initiate_failover(TENANT, from_region="us-east-1", to_region="us-east-1")

    event = await service.initiate_failover(TENANT, cluster_id="cluster-9", from_region="us-east-1", to_region="us-west-2")
    assert event.status == "initiated"

    event = await service.mark_in_progress(TENANT, event.id)
    assert event.status == "in_progress"

    event = await service.complete(TENANT, event.id)
    assert event.status == "completed"
    assert event.completed_at is not None

    with pytest.raises(FailoverError):
        await service.mark_in_progress(TENANT, event.id)


@pytest.mark.asyncio
async def test_plan_and_execution_not_found(repos):
    execution_service = RecoveryExecutionService(repos)
    with pytest.raises(NotFoundError):
        await execution_service.initiate_recovery(TENANT, "no-such-plan")
    with pytest.raises(NotFoundError):
        await execution_service.start(TENANT, "no-such-execution")
