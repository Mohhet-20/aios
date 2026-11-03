"""CI/CD platform: pipeline definitions, triggered runs with per-stage
tracking, deployment gates (manual/policy approval checkpoints within
a run), and releases (promotion + rollback).

A pipeline run's stage sequence is snapshotted from the pipeline's
`stages` list at trigger time — editing a pipeline's stage list later
does not retroactively change in-flight or historical runs, the same
"snapshot don't reference" posture used for prompt/workflow versioning
in earlier AIOS platforms."""
from __future__ import annotations

import asyncio
from collections import defaultdict


from infra_platform.config.settings import Settings, get_settings
from infra_platform.core.exceptions import (
    DeploymentGateBlockedError,
    NotFoundError,
    PipelineError,
    PipelineRunFailedError,
    ReleaseError,
    ValidationError,
)
from infra_platform.domain.entities import PipelineRun as PipelineRunEntity
from infra_platform.domain.enums import GateStatus, PipelineRunStatus, PipelineStageType, ReleaseStatus
from infra_platform.models.cicd import (
    DeploymentGateModel,
    PipelineModel,
    PipelineRunModel,
    PipelineStageRunModel,
    ReleaseModel,
)
from infra_platform.repositories.registry import RepositoryRegistry
from infra_platform.clock import utc_now

_VALID_STAGE_TYPES = {s.value for s in PipelineStageType}

_RELEASE_TRANSITIONS: dict[str, set[str]] = {
    ReleaseStatus.DRAFT.value: {ReleaseStatus.PENDING_APPROVAL.value},
    ReleaseStatus.PENDING_APPROVAL.value: {ReleaseStatus.APPROVED.value, ReleaseStatus.DRAFT.value},
    ReleaseStatus.APPROVED.value: {ReleaseStatus.RELEASED.value},
    ReleaseStatus.RELEASED.value: {ReleaseStatus.ROLLED_BACK.value},
    ReleaseStatus.ROLLED_BACK.value: set(),
}


def _to_run_entity(model: PipelineRunModel) -> PipelineRunEntity:
    return PipelineRunEntity(id=model.id, status=PipelineRunStatus(model.status))


class PipelineService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def create_pipeline(
        self, tenant_id: str, *, name: str, repository: str, default_branch: str = "main", stages: list[str] | None = None
    ) -> PipelineModel:
        stage_list = stages if stages is not None else [s.value for s in PipelineStageType]
        invalid = set(stage_list) - _VALID_STAGE_TYPES
        if invalid:
            raise ValidationError(f"Unknown pipeline stage type(s): {sorted(invalid)}")
        pipeline = PipelineModel(
            tenant_id=tenant_id, name=name, repository=repository, default_branch=default_branch,
            stages=stage_list, is_enabled=True,
        )
        return await self.repos.pipelines.add(pipeline)

    async def set_enabled(self, tenant_id: str, pipeline_id: str, *, enabled: bool) -> PipelineModel:
        pipeline = await self._get(tenant_id, pipeline_id)
        pipeline.is_enabled = enabled
        return await self.repos.pipelines.update(pipeline)

    async def _get(self, tenant_id: str, pipeline_id: str) -> PipelineModel:
        pipeline = await self.repos.pipelines.get(pipeline_id)
        if pipeline is None or pipeline.tenant_id != tenant_id:
            raise NotFoundError(f"Pipeline '{pipeline_id}' not found")
        return pipeline

    async def list_for_tenant(self, tenant_id: str) -> list[PipelineModel]:
        return await self.repos.pipelines.list_for_tenant(tenant_id)


class PipelineRunService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def trigger_run(
        self, tenant_id: str, pipeline_id: str, *, commit_sha: str, branch: str | None = None, triggered_by: str | None = None
    ) -> PipelineRunModel:
        pipeline = await self.repos.pipelines.get(pipeline_id)
        if pipeline is None or pipeline.tenant_id != tenant_id:
            raise NotFoundError(f"Pipeline '{pipeline_id}' not found")
        if not pipeline.is_enabled:
            raise PipelineError(f"Pipeline '{pipeline_id}' is disabled")

        run = await self.repos.pipeline_runs.add(
            PipelineRunModel(
                tenant_id=tenant_id, pipeline_id=pipeline_id, commit_sha=commit_sha,
                branch=branch or pipeline.default_branch, status=PipelineRunStatus.PENDING.value, triggered_by=triggered_by,
            )
        )
        for stage_type in pipeline.stages:
            await self.repos.pipeline_stage_runs.add(
                PipelineStageRunModel(tenant_id=tenant_id, run_id=run.id, stage_type=stage_type, status="pending")
            )
        return run

    async def _get(self, tenant_id: str, run_id: str) -> PipelineRunModel:
        run = await self.repos.pipeline_runs.get(run_id)
        if run is None or run.tenant_id != tenant_id:
            raise NotFoundError(f"PipelineRun '{run_id}' not found")
        return run

    async def start_run(self, tenant_id: str, run_id: str) -> PipelineRunModel:
        run = await self._get(tenant_id, run_id)
        entity = _to_run_entity(run)
        entity.start()
        run.status = entity.status.value
        return await self.repos.pipeline_runs.update(run)

    async def cancel_run(self, tenant_id: str, run_id: str) -> PipelineRunModel:
        run = await self._get(tenant_id, run_id)
        entity = _to_run_entity(run)
        entity.cancel()
        run.status = entity.status.value
        run.finished_at = entity.finished_at
        return await self.repos.pipeline_runs.update(run)

    async def start_stage(self, tenant_id: str, run_id: str, stage_type: str) -> PipelineStageRunModel:
        stage_run = await self._get_stage(tenant_id, run_id, stage_type)
        if stage_run.status != "pending":
            raise PipelineError(f"Stage '{stage_type}' on run '{run_id}' is not pending (status={stage_run.status})")
        stage_run.status = "running"
        return await self.repos.pipeline_stage_runs.update(stage_run)

    async def _get_stage(self, tenant_id: str, run_id: str, stage_type: str) -> PipelineStageRunModel:
        stages = await self.repos.pipeline_stage_runs.list_for_run(tenant_id, run_id)
        for s in stages:
            if s.stage_type == stage_type:
                return s
        raise NotFoundError(f"Stage '{stage_type}' not found for run '{run_id}'")

    async def complete_stage(
        self, tenant_id: str, run_id: str, stage_type: str, *, success: bool, logs_excerpt: str = ""
    ) -> PipelineStageRunModel:
        stage_run = await self._get_stage(tenant_id, run_id, stage_type)
        stage_run.status = "succeeded" if success else "failed"
        stage_run.logs_excerpt = logs_excerpt
        stage_run.finished_at = utc_now()
        stage_run = await self.repos.pipeline_stage_runs.update(stage_run)

        if not success:
            run = await self._get(tenant_id, run_id)
            entity = _to_run_entity(run)
            entity.fail()
            run.status = entity.status.value
            run.finished_at = entity.finished_at
            await self.repos.pipeline_runs.update(run)
            raise PipelineRunFailedError(f"Stage '{stage_type}' failed on run '{run_id}'")

        all_stages = await self.repos.pipeline_stage_runs.list_for_run(tenant_id, run_id)
        if all(s.status == "succeeded" for s in all_stages):
            run = await self._get(tenant_id, run_id)
            entity = _to_run_entity(run)
            entity.succeed()
            run.status = entity.status.value
            run.finished_at = entity.finished_at
            await self.repos.pipeline_runs.update(run)
        return stage_run

    async def list_runs_for_pipeline(self, tenant_id: str, pipeline_id: str) -> list[PipelineRunModel]:
        return await self.repos.pipeline_runs.list_for_pipeline(tenant_id, pipeline_id)

    async def list_stages(self, tenant_id: str, run_id: str) -> list[PipelineStageRunModel]:
        return await self.repos.pipeline_stage_runs.list_for_run(tenant_id, run_id)


class DeploymentGateService:
    """`approve`'s read-increment-threshold-check sequence spans
    multiple statements; two concurrent approvals on the same gate
    could otherwise both read the same `approvals_received` count and
    each write back count+1, losing one vote (or both independently
    conclude they crossed the threshold). Serialized per `gate_id`
    with an in-process `asyncio.Lock`, the same commit-spanning-lock
    pattern used throughout the AIOS build (e.g. the Security
    Platform's `ApprovalWorkflowService.record_decision`)."""

    _approval_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def create_gate(
        self, tenant_id: str, pipeline_run_id: str, *, name: str, required_approvals: int | None = None
    ) -> DeploymentGateModel:
        gate = DeploymentGateModel(
            tenant_id=tenant_id, pipeline_run_id=pipeline_run_id, name=name,
            status=GateStatus.PENDING.value,
            required_approvals=required_approvals if required_approvals is not None else 1,
            approvals_received=0,
        )
        return await self.repos.deployment_gates.add(gate)

    async def _get(self, tenant_id: str, gate_id: str) -> DeploymentGateModel:
        gate = await self.repos.deployment_gates.get(gate_id)
        if gate is None or gate.tenant_id != tenant_id:
            raise NotFoundError(f"DeploymentGate '{gate_id}' not found")
        return gate

    async def approve(self, tenant_id: str, gate_id: str) -> DeploymentGateModel:
        async with self._approval_locks[gate_id]:
            gate = await self._get(tenant_id, gate_id)
            if gate.status != GateStatus.PENDING.value:
                raise DeploymentGateBlockedError(f"Gate '{gate_id}' is not pending (status={gate.status})")
            gate.approvals_received += 1
            if gate.approvals_received >= gate.required_approvals:
                gate.status = GateStatus.APPROVED.value
            result = await self.repos.deployment_gates.update(gate)
            await self.repos.session.commit()
            return result

    async def reject(self, tenant_id: str, gate_id: str) -> DeploymentGateModel:
        gate = await self._get(tenant_id, gate_id)
        if gate.status != GateStatus.PENDING.value:
            raise DeploymentGateBlockedError(f"Gate '{gate_id}' is not pending (status={gate.status})")
        gate.status = GateStatus.REJECTED.value
        return await self.repos.deployment_gates.update(gate)

    async def bypass(self, tenant_id: str, gate_id: str) -> DeploymentGateModel:
        gate = await self._get(tenant_id, gate_id)
        if gate.status != GateStatus.PENDING.value:
            raise DeploymentGateBlockedError(f"Gate '{gate_id}' is not pending (status={gate.status})")
        gate.status = GateStatus.BYPASSED.value
        return await self.repos.deployment_gates.update(gate)

    async def ensure_open(self, tenant_id: str, gate_id: str) -> DeploymentGateModel:
        gate = await self._get(tenant_id, gate_id)
        if gate.status not in (GateStatus.APPROVED.value, GateStatus.BYPASSED.value):
            raise DeploymentGateBlockedError(f"Gate '{gate_id}' is not open (status={gate.status})")
        return gate

    async def list_for_run(self, tenant_id: str, pipeline_run_id: str) -> list[DeploymentGateModel]:
        return await self.repos.deployment_gates.list_for_run(tenant_id, pipeline_run_id)


class ReleaseService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def create_release(
        self, tenant_id: str, *, name: str, version: str, pipeline_run_id: str | None = None
    ) -> ReleaseModel:
        existing = await self.repos.releases.get_by_name_version(tenant_id, name, version)
        if existing is not None:
            raise ReleaseError(f"Release '{name}@{version}' already exists")
        release = ReleaseModel(
            tenant_id=tenant_id, name=name, version=version, status=ReleaseStatus.DRAFT.value, pipeline_run_id=pipeline_run_id,
        )
        return await self.repos.releases.add(release)

    async def _get(self, tenant_id: str, release_id: str) -> ReleaseModel:
        release = await self.repos.releases.get(release_id)
        if release is None or release.tenant_id != tenant_id:
            raise NotFoundError(f"Release '{release_id}' not found")
        return release

    async def _transition(self, tenant_id: str, release_id: str, target: str) -> ReleaseModel:
        release = await self._get(tenant_id, release_id)
        allowed = _RELEASE_TRANSITIONS.get(release.status, set())
        if target not in allowed:
            raise ReleaseError(f"Release '{release_id}' cannot transition from {release.status} to {target}")
        release.status = target
        if target == ReleaseStatus.RELEASED.value:
            release.released_at = utc_now()
        elif target == ReleaseStatus.ROLLED_BACK.value:
            release.rolled_back_at = utc_now()
        return await self.repos.releases.update(release)

    async def submit_for_approval(self, tenant_id: str, release_id: str) -> ReleaseModel:
        return await self._transition(tenant_id, release_id, ReleaseStatus.PENDING_APPROVAL.value)

    async def approve(self, tenant_id: str, release_id: str) -> ReleaseModel:
        return await self._transition(tenant_id, release_id, ReleaseStatus.APPROVED.value)

    async def publish(self, tenant_id: str, release_id: str) -> ReleaseModel:
        return await self._transition(tenant_id, release_id, ReleaseStatus.RELEASED.value)

    async def rollback(self, tenant_id: str, release_id: str) -> ReleaseModel:
        return await self._transition(tenant_id, release_id, ReleaseStatus.ROLLED_BACK.value)

    async def list_for_tenant(self, tenant_id: str) -> list[ReleaseModel]:
        return await self.repos.releases.list_for_tenant(tenant_id)
