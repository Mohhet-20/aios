import pytest

from prompt_platform.core.exceptions import EvalGateNotMetError, InvalidTransitionError
from prompt_platform.domain.enums import VersionBranch
from prompt_platform.models.prompt import PromptModel
from prompt_platform.models.workspace import PromptProjectModel, PromptWorkspaceModel
from prompt_platform.prompt_engine.versioning_service import VersioningService


async def _seed_prompt(repos):
    ws = await repos.workspaces.add(PromptWorkspaceModel(name="WS", slug="ws", organization_id="org1"))
    proj = await repos.projects.add(PromptProjectModel(workspace_id=ws.id, name="Proj", slug="proj"))
    prompt = await repos.prompts.add(PromptModel(project_id=proj.id, workspace_id=ws.id, name="Greeting", slug="greeting", owner_id="u1"))
    return prompt


@pytest.mark.asyncio
async def test_create_version_increments_number(repos):
    svc = VersioningService(repos)
    prompt = await _seed_prompt(repos)
    v1 = await svc.create_version(prompt.id, user_template="Hi {{name}}", actor_id="u1")
    v2 = await svc.create_version(prompt.id, user_template="Hello {{name}}", actor_id="u1", parent_version_id=v1.id)
    assert v1.version_number == 1
    assert v2.version_number == 2
    assert v2.parent_version_id == v1.id

    refreshed_prompt = await repos.prompts.get(prompt.id)
    assert refreshed_prompt.latest_version_number == 2


@pytest.mark.asyncio
async def test_full_approval_workflow(repos):
    svc = VersioningService(repos, min_production_eval_score=80.0)
    prompt = await _seed_prompt(repos)
    v1 = await svc.create_version(prompt.id, user_template="Hi", actor_id="u1")

    await svc.submit_for_review(v1.id, "u1")
    approved = await svc.approve(v1.id, "reviewer1")
    assert approved.status == "approved"

    with pytest.raises(EvalGateNotMetError):
        await svc.promote(prompt.id, v1.id, VersionBranch.PRODUCTION, "reviewer1")

    await svc.record_eval_score(v1.id, 92.0)
    promoted = await svc.promote(prompt.id, v1.id, VersionBranch.PRODUCTION, "reviewer1", release_notes="initial launch")
    assert promoted.branch == "production"

    refreshed_prompt = await repos.prompts.get(prompt.id)
    assert refreshed_prompt.production_version_id == v1.id

    releases = await repos.releases.list_for_prompt(prompt.id)
    assert len(releases) == 1
    assert releases[0].release_notes == "initial launch"


@pytest.mark.asyncio
async def test_promoting_new_version_demotes_previous_production_to_stable(repos):
    svc = VersioningService(repos, min_production_eval_score=80.0)
    prompt = await _seed_prompt(repos)
    v1 = await svc.create_version(prompt.id, user_template="v1", actor_id="u1")
    v2 = await svc.create_version(prompt.id, user_template="v2", actor_id="u1")

    for v in (v1, v2):
        await svc.submit_for_review(v.id, "u1")
        await svc.approve(v.id, "reviewer1")
        await svc.record_eval_score(v.id, 95.0)

    await svc.promote(prompt.id, v1.id, VersionBranch.PRODUCTION, "reviewer1")
    await svc.promote(prompt.id, v2.id, VersionBranch.PRODUCTION, "reviewer1")

    v1_refreshed = await repos.versions.get(v1.id)
    v2_refreshed = await repos.versions.get(v2.id)
    prompt_refreshed = await repos.prompts.get(prompt.id)

    assert v1_refreshed.branch == "stable"
    assert v2_refreshed.branch == "production"
    assert prompt_refreshed.production_version_id == v2.id
    assert prompt_refreshed.stable_version_id == v1.id


@pytest.mark.asyncio
async def test_rollback_restores_previous_production_version(repos):
    svc = VersioningService(repos, min_production_eval_score=80.0)
    prompt = await _seed_prompt(repos)
    v1 = await svc.create_version(prompt.id, user_template="v1", actor_id="u1")
    v2 = await svc.create_version(prompt.id, user_template="v2 (buggy)", actor_id="u1")

    for v in (v1, v2):
        await svc.submit_for_review(v.id, "u1")
        await svc.approve(v.id, "reviewer1")
        await svc.record_eval_score(v.id, 95.0)

    await svc.promote(prompt.id, v1.id, VersionBranch.PRODUCTION, "reviewer1")
    await svc.promote(prompt.id, v2.id, VersionBranch.PRODUCTION, "reviewer1")

    await svc.rollback(prompt.id, v1.id, "reviewer1", reason="v2 regressed")

    prompt_refreshed = await repos.prompts.get(prompt.id)
    v1_refreshed = await repos.versions.get(v1.id)
    v2_refreshed = await repos.versions.get(v2.id)
    assert prompt_refreshed.production_version_id == v1.id
    assert v1_refreshed.branch == "production"
    assert v2_refreshed.branch == "stable"


@pytest.mark.asyncio
async def test_reject_records_reason_and_history(repos):
    svc = VersioningService(repos)
    prompt = await _seed_prompt(repos)
    v1 = await svc.create_version(prompt.id, user_template="hi", actor_id="u1")
    await svc.submit_for_review(v1.id, "u1")
    rejected = await svc.reject(v1.id, "reviewer1", "unclear tone")
    assert rejected.status == "rejected"
    assert rejected.rejection_reason == "unclear tone"

    history = await svc.history(prompt.id)
    actions = [h.action for h in history]
    assert "version_rejected" in actions
    assert "version_submitted_for_review" in actions


@pytest.mark.asyncio
async def test_diff_versions_reports_template_and_parameter_changes(repos):
    svc = VersioningService(repos)
    prompt = await _seed_prompt(repos)
    v1 = await svc.create_version(prompt.id, user_template="Hello there", actor_id="u1", parameters={"temperature": 0.5})
    v2 = await svc.create_version(prompt.id, user_template="Hello world", actor_id="u1", parameters={"temperature": 0.9, "model": "gpt-4o"})

    diff = await svc.diff_versions(v1.id, v2.id)
    assert any("Hello" in line or "+" in line for line in diff["user_template_diff"])
    assert diff["parameter_changes"]["changed"]["temperature"] == {"from": 0.5, "to": 0.9}
    assert diff["parameter_changes"]["added"] == {"model": "gpt-4o"}


@pytest.mark.asyncio
async def test_promote_without_approval_raises(repos):
    svc = VersioningService(repos)
    prompt = await _seed_prompt(repos)
    v1 = await svc.create_version(prompt.id, user_template="hi", actor_id="u1")
    with pytest.raises(InvalidTransitionError):
        await svc.promote(prompt.id, v1.id, VersionBranch.STABLE, "u1")
