"""Disaster Recovery API: backups, snapshots, recovery plans,
guarded recovery executions, and cross-region failover events."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from infra_platform.dependencies.dependencies import (
    get_backup_service,
    get_current_tenant_id,
    get_failover_service,
    get_recovery_execution_service,
    get_recovery_plan_service,
    get_snapshot_service,
)
from infra_platform.infra_api.serialization import to_dict, to_dict_list
from infra_platform.recovery.recovery_service import (
    BackupService,
    FailoverService,
    RecoveryExecutionService,
    RecoveryPlanService,
    SnapshotService,
)

router = APIRouter(prefix="/recovery", tags=["disaster-recovery"])


class CreateBackupRequest(BaseModel):
    resource_type: str
    resource_id: str


@router.post("/backups", status_code=201)
async def create_backup(body: CreateBackupRequest, tenant_id: str = Depends(get_current_tenant_id), service: BackupService = Depends(get_backup_service)):
    return to_dict(await service.create_backup(tenant_id, **body.model_dump()))


@router.post("/backups/{backup_id}/start")
async def start_backup(backup_id: str, tenant_id: str = Depends(get_current_tenant_id), service: BackupService = Depends(get_backup_service)):
    return to_dict(await service.start_backup(tenant_id, backup_id))


class CompleteBackupRequest(BaseModel):
    size_bytes: int | None = None
    storage_uri: str | None = None


@router.post("/backups/{backup_id}/complete")
async def complete_backup(backup_id: str, body: CompleteBackupRequest, tenant_id: str = Depends(get_current_tenant_id), service: BackupService = Depends(get_backup_service)):
    return to_dict(await service.complete_backup(tenant_id, backup_id, **body.model_dump()))


@router.post("/backups/{backup_id}/fail")
async def fail_backup(backup_id: str, tenant_id: str = Depends(get_current_tenant_id), service: BackupService = Depends(get_backup_service)):
    return to_dict(await service.fail_backup(tenant_id, backup_id))


@router.get("/backups")
async def list_backups(resource_type: str, resource_id: str, tenant_id: str = Depends(get_current_tenant_id), service: BackupService = Depends(get_backup_service)):
    return to_dict_list(await service.list_for_resource(tenant_id, resource_type, resource_id))


@router.post("/backups/prune")
async def prune_backups(resource_type: str, resource_id: str, tenant_id: str = Depends(get_current_tenant_id), service: BackupService = Depends(get_backup_service)):
    return {"pruned": await service.prune_expired(tenant_id, resource_type, resource_id)}


class TakeSnapshotRequest(BaseModel):
    resource_type: str
    resource_id: str
    backup_id: str | None = None
    storage_uri: str | None = None


@router.post("/snapshots", status_code=201)
async def take_snapshot(body: TakeSnapshotRequest, tenant_id: str = Depends(get_current_tenant_id), service: SnapshotService = Depends(get_snapshot_service)):
    return to_dict(await service.take_snapshot(tenant_id, **body.model_dump()))


@router.get("/snapshots")
async def list_snapshots(resource_type: str, resource_id: str, tenant_id: str = Depends(get_current_tenant_id), service: SnapshotService = Depends(get_snapshot_service)):
    return to_dict_list(await service.list_for_resource(tenant_id, resource_type, resource_id))


class CreatePlanRequest(BaseModel):
    name: str
    resource_type: str
    rpo_minutes: int | None = None
    rto_minutes: int | None = None
    target_region: str | None = None


@router.post("/plans", status_code=201)
async def create_plan(body: CreatePlanRequest, tenant_id: str = Depends(get_current_tenant_id), service: RecoveryPlanService = Depends(get_recovery_plan_service)):
    return to_dict(await service.create_plan(tenant_id, **body.model_dump()))


@router.get("/plans")
async def list_active_plans(tenant_id: str = Depends(get_current_tenant_id), service: RecoveryPlanService = Depends(get_recovery_plan_service)):
    return to_dict_list(await service.list_active(tenant_id))


@router.post("/plans/{plan_id}/deactivate")
async def deactivate_plan(plan_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RecoveryPlanService = Depends(get_recovery_plan_service)):
    return to_dict(await service.deactivate(tenant_id, plan_id))


@router.post("/plans/{plan_id}/activate")
async def activate_plan(plan_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RecoveryPlanService = Depends(get_recovery_plan_service)):
    return to_dict(await service.activate(tenant_id, plan_id))


class InitiateRecoveryRequest(BaseModel):
    notes: str | None = None


@router.post("/plans/{plan_id}/executions", status_code=201)
async def initiate_recovery(plan_id: str, body: InitiateRecoveryRequest, tenant_id: str = Depends(get_current_tenant_id), service: RecoveryExecutionService = Depends(get_recovery_execution_service)):
    return to_dict(await service.initiate_recovery(tenant_id, plan_id, **body.model_dump()))


@router.get("/plans/{plan_id}/executions")
async def list_executions(plan_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RecoveryExecutionService = Depends(get_recovery_execution_service)):
    return to_dict_list(await service.list_for_plan(tenant_id, plan_id))


@router.post("/executions/{execution_id}/start")
async def start_execution(execution_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RecoveryExecutionService = Depends(get_recovery_execution_service)):
    return to_dict(await service.start(tenant_id, execution_id))


@router.post("/executions/{execution_id}/complete")
async def complete_execution(execution_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RecoveryExecutionService = Depends(get_recovery_execution_service)):
    return to_dict(await service.complete(tenant_id, execution_id))


@router.post("/executions/{execution_id}/fail")
async def fail_execution(execution_id: str, tenant_id: str = Depends(get_current_tenant_id), service: RecoveryExecutionService = Depends(get_recovery_execution_service)):
    return to_dict(await service.fail(tenant_id, execution_id))


class InitiateFailoverRequest(BaseModel):
    cluster_id: str | None = None
    from_region: str
    to_region: str


@router.post("/failovers", status_code=201)
async def initiate_failover(body: InitiateFailoverRequest, tenant_id: str = Depends(get_current_tenant_id), service: FailoverService = Depends(get_failover_service)):
    return to_dict(await service.initiate_failover(tenant_id, **body.model_dump()))


@router.get("/failovers")
async def list_failovers(cluster_id: str, tenant_id: str = Depends(get_current_tenant_id), service: FailoverService = Depends(get_failover_service)):
    return to_dict_list(await service.list_for_cluster(tenant_id, cluster_id))


@router.post("/failovers/{event_id}/in-progress")
async def mark_failover_in_progress(event_id: str, tenant_id: str = Depends(get_current_tenant_id), service: FailoverService = Depends(get_failover_service)):
    return to_dict(await service.mark_in_progress(tenant_id, event_id))


@router.post("/failovers/{event_id}/complete")
async def complete_failover(event_id: str, tenant_id: str = Depends(get_current_tenant_id), service: FailoverService = Depends(get_failover_service)):
    return to_dict(await service.complete(tenant_id, event_id))


@router.post("/failovers/{event_id}/fail")
async def fail_failover(event_id: str, tenant_id: str = Depends(get_current_tenant_id), service: FailoverService = Depends(get_failover_service)):
    return to_dict(await service.fail(tenant_id, event_id))
