"""Tests for the CI/CD platform: pipeline definitions, triggered runs
with stage tracking (success and failure paths), deployment gates, and
release promotion/rollback."""
from __future__ import annotations

import pytest

from infra_platform.cicd.cicd_service import (
    DeploymentGateService,
    PipelineRunService,
    PipelineService,
    ReleaseService,
)
from infra_platform.core.exceptions import (
    DeploymentGateBlockedError,
    NotFoundError,
    PipelineError,
    PipelineRunFailedError,
    ReleaseError,
    ValidationError,
)

TENANT = "tenant-cicd"


@pytest.mark.asyncio
async def test_create_pipeline_defaults_to_full_stage_list(repos):
    service = PipelineService(repos)
    pipeline = await service.create_pipeline(TENANT, name="api-pipeline", repository="org/api")
    assert pipeline.stages == ["build", "test", "static_analysis", "security_scan", "publish", "deploy"]
    assert pipeline.is_enabled is True


@pytest.mark.asyncio
async def test_create_pipeline_rejects_unknown_stage(repos):
    service = PipelineService(repos)
    with pytest.raises(ValidationError):
        await service.create_pipeline(TENANT, name="bad", repository="org/bad", stages=["build", "teleport"])


@pytest.mark.asyncio
async def test_disabled_pipeline_cannot_be_triggered(repos):
    pipeline_service = PipelineService(repos)
    run_service = PipelineRunService(repos)
    pipeline = await pipeline_service.create_pipeline(TENANT, name="p", repository="org/p", stages=["build", "test"])
    await pipeline_service.set_enabled(TENANT, pipeline.id, enabled=False)

    with pytest.raises(PipelineError):
        await run_service.trigger_run(TENANT, pipeline.id, commit_sha="abc123")


@pytest.mark.asyncio
async def test_run_happy_path_all_stages_succeed(repos):
    pipeline_service = PipelineService(repos)
    run_service = PipelineRunService(repos)
    pipeline = await pipeline_service.create_pipeline(TENANT, name="p2", repository="org/p2", stages=["build", "test", "deploy"])

    run = await run_service.trigger_run(TENANT, pipeline.id, commit_sha="deadbeef", triggered_by="ci-bot")
    assert run.status == "pending"
    stages = await run_service.list_stages(TENANT, run.id)
    assert [s.stage_type for s in stages] == ["build", "test", "deploy"]

    run = await run_service.start_run(TENANT, run.id)
    assert run.status == "running"

    for stage in ["build", "test"]:
        await run_service.start_stage(TENANT, run.id, stage)
        await run_service.complete_stage(TENANT, run.id, stage, success=True)

    await run_service.start_stage(TENANT, run.id, "deploy")
    await run_service.complete_stage(TENANT, run.id, "deploy", success=True)

    final = await run_service._get(TENANT, run.id)
    assert final.status == "succeeded"


@pytest.mark.asyncio
async def test_run_fails_on_stage_failure(repos):
    pipeline_service = PipelineService(repos)
    run_service = PipelineRunService(repos)
    pipeline = await pipeline_service.create_pipeline(TENANT, name="p3", repository="org/p3", stages=["build", "test"])
    run = await run_service.trigger_run(TENANT, pipeline.id, commit_sha="cafebabe")
    await run_service.start_run(TENANT, run.id)

    await run_service.start_stage(TENANT, run.id, "build")
    await run_service.complete_stage(TENANT, run.id, "build", success=True)

    await run_service.start_stage(TENANT, run.id, "test")
    with pytest.raises(PipelineRunFailedError):
        await run_service.complete_stage(TENANT, run.id, "test", success=False, logs_excerpt="assertion error")

    final = await run_service._get(TENANT, run.id)
    assert final.status == "failed"
    assert final.finished_at is not None


@pytest.mark.asyncio
async def test_deployment_gate_multi_approval_threshold(repos):
    gate_service = DeploymentGateService(repos)
    gate = await gate_service.create_gate(TENANT, "run-1", name="prod-gate", required_approvals=2)
    assert gate.status == "pending"

    gate = await gate_service.approve(TENANT, gate.id)
    assert gate.status == "pending"
    assert gate.approvals_received == 1

    gate = await gate_service.approve(TENANT, gate.id)
    assert gate.status == "approved"
    assert gate.approvals_received == 2

    with pytest.raises(DeploymentGateBlockedError):
        await gate_service.approve(TENANT, gate.id)


@pytest.mark.asyncio
async def test_deployment_gate_reject_and_bypass(repos):
    gate_service = DeploymentGateService(repos)
    gate = await gate_service.create_gate(TENANT, "run-2", name="staging-gate")
    gate = await gate_service.reject(TENANT, gate.id)
    assert gate.status == "rejected"
    with pytest.raises(DeploymentGateBlockedError):
        await gate_service.ensure_open(TENANT, gate.id)

    gate2 = await gate_service.create_gate(TENANT, "run-3", name="bypass-gate")
    gate2 = await gate_service.bypass(TENANT, gate2.id)
    opened = await gate_service.ensure_open(TENANT, gate2.id)
    assert opened.status == "bypassed"


@pytest.mark.asyncio
async def test_release_promotion_and_rollback(repos):
    release_service = ReleaseService(repos)
    release = await release_service.create_release(TENANT, name="aios-core", version="2.4.0")
    assert release.status == "draft"

    with pytest.raises(ReleaseError):
        await release_service.create_release(TENANT, name="aios-core", version="2.4.0")

    release = await release_service.submit_for_approval(TENANT, release.id)
    assert release.status == "pending_approval"

    release = await release_service.approve(TENANT, release.id)
    assert release.status == "approved"

    release = await release_service.publish(TENANT, release.id)
    assert release.status == "released"
    assert release.released_at is not None

    release = await release_service.rollback(TENANT, release.id)
    assert release.status == "rolled_back"
    assert release.rolled_back_at is not None

    with pytest.raises(ReleaseError):
        await release_service.publish(TENANT, release.id)


@pytest.mark.asyncio
async def test_pipeline_run_not_found_raises(repos):
    run_service = PipelineRunService(repos)
    with pytest.raises(NotFoundError):
        await run_service.start_run(TENANT, "no-such-run")
