import pytest

from prompt_platform.core.exceptions import ApprovalRequiredError, DeploymentError, InvalidTransitionError, ValidationError
from prompt_platform.domain.enums import DeploymentEnvironment, DeploymentStatus, VersionStatus
from prompt_platform.models.prompt import PromptModel
from prompt_platform.models.version import PromptVersionModel
from prompt_platform.models.workspace import PromptProjectModel, PromptWorkspaceModel
from prompt_platform.prompt_deployment.deployment_service import DeploymentService


async def _seed(repos, *, status=VersionStatus.APPROVED.value, eval_score=90.0):
    ws = await repos.workspaces.add(PromptWorkspaceModel(name="WS", slug="ws-dep", organization_id="org1"))
    proj = await repos.projects.add(PromptProjectModel(workspace_id=ws.id, name="Proj", slug="proj-dep"))
    prompt = await repos.prompts.add(PromptModel(project_id=proj.id, workspace_id=ws.id, name="QA", slug="qa-dep", owner_id="u1"))
    version = await repos.versions.add(
        PromptVersionModel(prompt_id=prompt.id, version_number=1, user_template="Answer {{q}}.", status=status, eval_score=eval_score)
    )
    return ws, prompt, version


@pytest.mark.asyncio
async def test_dev_deployment_auto_approves(repos):
    ws, prompt, version = await _seed(repos, status=VersionStatus.DRAFT.value, eval_score=None)
    svc = DeploymentService(repos)
    deployment = await svc.request_deployment(prompt.id, version.id, DeploymentEnvironment.DEVELOPMENT, requested_by="u1")
    assert deployment.status == DeploymentStatus.APPROVED.value
    assert deployment.approved_by == "u1"


@pytest.mark.asyncio
async def test_staging_requires_approved_version(repos):
    ws, prompt, version = await _seed(repos, status=VersionStatus.DRAFT.value)
    svc = DeploymentService(repos)
    with pytest.raises(ApprovalRequiredError):
        await svc.request_deployment(prompt.id, version.id, DeploymentEnvironment.STAGING, requested_by="u1")


@pytest.mark.asyncio
async def test_staging_deployment_pending_approval_when_version_approved(repos):
    ws, prompt, version = await _seed(repos)
    svc = DeploymentService(repos)
    deployment = await svc.request_deployment(prompt.id, version.id, DeploymentEnvironment.STAGING, requested_by="u1")
    assert deployment.status == DeploymentStatus.PENDING_APPROVAL.value
    assert deployment.approved_by is None


@pytest.mark.asyncio
async def test_production_requires_eval_gate(repos):
    ws, prompt, version = await _seed(repos, eval_score=50.0)
    svc = DeploymentService(repos, min_production_eval_score=85.0)
    with pytest.raises(ApprovalRequiredError):
        await svc.request_deployment(prompt.id, version.id, DeploymentEnvironment.PRODUCTION, requested_by="u1")


@pytest.mark.asyncio
async def test_full_approval_and_deploy_flow(repos):
    ws, prompt, version = await _seed(repos)
    svc = DeploymentService(repos)
    deployment = await svc.request_deployment(prompt.id, version.id, DeploymentEnvironment.STAGING, requested_by="u1")

    approved = await svc.approve(deployment.id, approved_by="reviewer1")
    assert approved.status == DeploymentStatus.APPROVED.value
    assert approved.approved_by == "reviewer1"

    deployed = await svc.deploy(deployment.id, actor_id="reviewer1")
    assert deployed.status == DeploymentStatus.DEPLOYED.value
    assert deployed.deployed_at is not None

    current = await svc.get_current(prompt.id, DeploymentEnvironment.STAGING)
    assert current.id == deployment.id


@pytest.mark.asyncio
async def test_cannot_deploy_before_approval(repos):
    ws, prompt, version = await _seed(repos)
    svc = DeploymentService(repos)
    deployment = await svc.request_deployment(prompt.id, version.id, DeploymentEnvironment.STAGING, requested_by="u1")
    with pytest.raises(InvalidTransitionError):
        await svc.deploy(deployment.id, actor_id="u1")


@pytest.mark.asyncio
async def test_reject_deployment(repos):
    ws, prompt, version = await _seed(repos)
    svc = DeploymentService(repos)
    deployment = await svc.request_deployment(prompt.id, version.id, DeploymentEnvironment.STAGING, requested_by="u1")
    rejected = await svc.reject(deployment.id, actor_id="reviewer1", reason="not ready")
    assert rejected.status == DeploymentStatus.REJECTED.value
    with pytest.raises(InvalidTransitionError):
        await svc.approve(deployment.id, approved_by="reviewer1")


@pytest.mark.asyncio
async def test_canary_rollout_and_promotion(repos):
    ws, prompt, version = await _seed(repos)
    svc = DeploymentService(repos)
    deployment = await svc.request_deployment(prompt.id, version.id, DeploymentEnvironment.PRODUCTION, requested_by="u1", canary_percent=10.0)
    await svc.approve(deployment.id, approved_by="reviewer1")
    deployed = await svc.deploy(deployment.id, actor_id="reviewer1")
    assert deployed.canary_percent == 10.0

    widened = await svc.promote_canary(deployment.id, actor_id="reviewer1", canary_percent=50.0)
    assert widened.canary_percent == 50.0

    full = await svc.promote_canary(deployment.id, actor_id="reviewer1")
    assert full.canary_percent == 100.0


@pytest.mark.asyncio
async def test_promote_canary_requires_deployed_status(repos):
    ws, prompt, version = await _seed(repos)
    svc = DeploymentService(repos)
    deployment = await svc.request_deployment(prompt.id, version.id, DeploymentEnvironment.STAGING, requested_by="u1")
    with pytest.raises(InvalidTransitionError):
        await svc.promote_canary(deployment.id, actor_id="u1")


@pytest.mark.asyncio
async def test_rollback_to_previous_version(repos):
    ws, prompt, version_a = await _seed(repos)
    version_b = await repos.versions.add(
        PromptVersionModel(prompt_id=prompt.id, version_number=2, user_template="Answer {{q}} differently.", status=VersionStatus.APPROVED.value, eval_score=95.0)
    )
    svc = DeploymentService(repos)

    dep1 = await svc.request_deployment(prompt.id, version_a.id, DeploymentEnvironment.PRODUCTION, requested_by="u1")
    await svc.approve(dep1.id, approved_by="r1")
    await svc.deploy(dep1.id, actor_id="r1")

    dep2 = await svc.request_deployment(prompt.id, version_b.id, DeploymentEnvironment.PRODUCTION, requested_by="u1")
    await svc.approve(dep2.id, approved_by="r1")
    await svc.deploy(dep2.id, actor_id="r1")

    current = await svc.get_current(prompt.id, DeploymentEnvironment.PRODUCTION)
    assert current.id == dep2.id

    rolled_back = await svc.rollback(prompt.id, DeploymentEnvironment.PRODUCTION, actor_id="oncall1", reason="regression")
    assert rolled_back.version_id == version_a.id
    assert rolled_back.status == DeploymentStatus.DEPLOYED.value
    assert rolled_back.rollback_of_id == dep2.id

    refreshed_dep2 = await repos.deployments.get(dep2.id)
    assert refreshed_dep2.status == DeploymentStatus.ROLLED_BACK.value

    new_current = await svc.get_current(prompt.id, DeploymentEnvironment.PRODUCTION)
    assert new_current.id == rolled_back.id


@pytest.mark.asyncio
async def test_rollback_to_explicit_target_version(repos):
    ws, prompt, version_a = await _seed(repos)
    version_b = await repos.versions.add(
        PromptVersionModel(prompt_id=prompt.id, version_number=2, user_template="v2", status=VersionStatus.APPROVED.value, eval_score=95.0)
    )
    version_c = await repos.versions.add(
        PromptVersionModel(prompt_id=prompt.id, version_number=3, user_template="v3", status=VersionStatus.APPROVED.value, eval_score=95.0)
    )
    svc = DeploymentService(repos)
    for v in (version_a, version_b, version_c):
        d = await svc.request_deployment(prompt.id, v.id, DeploymentEnvironment.PRODUCTION, requested_by="u1")
        await svc.approve(d.id, approved_by="r1")
        await svc.deploy(d.id, actor_id="r1")

    rolled_back = await svc.rollback(prompt.id, DeploymentEnvironment.PRODUCTION, actor_id="oncall1", target_version_id=version_a.id)
    assert rolled_back.version_id == version_a.id


@pytest.mark.asyncio
async def test_rollback_without_history_raises(repos):
    ws, prompt, version = await _seed(repos)
    svc = DeploymentService(repos)
    with pytest.raises(DeploymentError):
        await svc.rollback(prompt.id, DeploymentEnvironment.PRODUCTION, actor_id="u1")


@pytest.mark.asyncio
async def test_rollback_with_no_prior_deployment_raises(repos):
    ws, prompt, version = await _seed(repos)
    svc = DeploymentService(repos)
    d = await svc.request_deployment(prompt.id, version.id, DeploymentEnvironment.PRODUCTION, requested_by="u1")
    await svc.approve(d.id, approved_by="r1")
    await svc.deploy(d.id, actor_id="r1")
    with pytest.raises(DeploymentError):
        await svc.rollback(prompt.id, DeploymentEnvironment.PRODUCTION, actor_id="u1")


@pytest.mark.asyncio
async def test_invalid_canary_percent_rejected(repos):
    ws, prompt, version = await _seed(repos)
    svc = DeploymentService(repos)
    with pytest.raises(ValidationError):
        await svc.request_deployment(prompt.id, version.id, DeploymentEnvironment.DEVELOPMENT, requested_by="u1", canary_percent=0.0)


@pytest.mark.asyncio
async def test_environment_config_upsert(repos):
    ws, prompt, version = await _seed(repos)
    svc = DeploymentService(repos)
    created = await svc.set_environment_config(ws.id, DeploymentEnvironment.PRODUCTION, {"MAX_RETRIES": "3"}, updated_by="u1")
    assert created.variables == {"MAX_RETRIES": "3"}

    updated = await svc.set_environment_config(ws.id, DeploymentEnvironment.PRODUCTION, {"MAX_RETRIES": "5"}, updated_by="u2")
    assert updated.id == created.id
    assert updated.variables == {"MAX_RETRIES": "5"}

    fetched = await svc.get_environment_config(ws.id, DeploymentEnvironment.PRODUCTION)
    assert fetched == {"MAX_RETRIES": "5"}

    empty = await svc.get_environment_config(ws.id, DeploymentEnvironment.STAGING)
    assert empty == {}


@pytest.mark.asyncio
async def test_history_lists_all_deployments_for_prompt(repos):
    ws, prompt, version = await _seed(repos)
    svc = DeploymentService(repos)
    await svc.request_deployment(prompt.id, version.id, DeploymentEnvironment.DEVELOPMENT, requested_by="u1")
    await svc.request_deployment(prompt.id, version.id, DeploymentEnvironment.STAGING, requested_by="u1")
    all_history = await svc.history(prompt.id)
    assert len(all_history) == 2
    staging_only = await svc.history(prompt.id, environment=DeploymentEnvironment.STAGING)
    assert len(staging_only) == 1
