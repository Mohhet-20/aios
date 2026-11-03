import pytest

from eval_platform.core.exceptions import ValidationError


@pytest.mark.asyncio
async def test_get_or_create_draft_creates_first_version(version_service, evaluation_service, workspace):
    evaluation = await evaluation_service.create_evaluation(workspace.id, name="E1", owner_id="u1", category="prompt", organization_id="org-1")
    draft = await version_service.get_or_create_draft(evaluation.id, created_by="u1")
    assert draft.version_number == 1
    assert draft.status == "draft"


@pytest.mark.asyncio
async def test_get_or_create_draft_is_idempotent(version_service, evaluation_service, workspace):
    evaluation = await evaluation_service.create_evaluation(workspace.id, name="E1", owner_id="u1", category="prompt", organization_id="org-1")
    d1 = await version_service.get_or_create_draft(evaluation.id, created_by="u1")
    d2 = await version_service.get_or_create_draft(evaluation.id, created_by="u1")
    assert d1.id == d2.id


@pytest.mark.asyncio
async def test_publish_requires_metric_keys(version_service, evaluation_service, workspace):
    evaluation = await evaluation_service.create_evaluation(workspace.id, name="E1", owner_id="u1", category="prompt", organization_id="org-1")
    draft = await version_service.get_or_create_draft(evaluation.id, created_by="u1")
    await version_service.update_draft(draft.id, target_config={"type": "prompt", "ref_id": "p1"})
    with pytest.raises(ValidationError):
        await version_service.publish_version(draft.id)


@pytest.mark.asyncio
async def test_publish_requires_target_config(version_service, evaluation_service, workspace):
    evaluation = await evaluation_service.create_evaluation(workspace.id, name="E1", owner_id="u1", category="prompt", organization_id="org-1")
    draft = await version_service.get_or_create_draft(evaluation.id, created_by="u1")
    await version_service.update_draft(draft.id, metric_keys=["accuracy"])
    with pytest.raises(ValidationError):
        await version_service.publish_version(draft.id)


@pytest.mark.asyncio
async def test_publish_rejects_out_of_range_threshold(version_service, evaluation_service, workspace):
    evaluation = await evaluation_service.create_evaluation(workspace.id, name="E1", owner_id="u1", category="prompt", organization_id="org-1")
    draft = await version_service.get_or_create_draft(evaluation.id, created_by="u1")
    await version_service.update_draft(draft.id, metric_keys=["accuracy"], target_config={"type": "prompt"}, pass_threshold=1.5)
    with pytest.raises(ValidationError):
        await version_service.publish_version(draft.id)


@pytest.mark.asyncio
async def test_publish_activates_evaluation(version_service, evaluation_service, workspace):
    evaluation = await evaluation_service.create_evaluation(workspace.id, name="E1", owner_id="u1", category="prompt", organization_id="org-1")
    draft = await version_service.get_or_create_draft(evaluation.id, created_by="u1")
    await version_service.update_draft(draft.id, metric_keys=["accuracy"], target_config={"type": "prompt", "ref_id": "p1"}, pass_threshold=0.8)
    published = await version_service.publish_version(draft.id)
    assert published.status == "published"

    refreshed = await evaluation_service.get_evaluation(evaluation.id)
    assert refreshed.status == "active"
    assert refreshed.current_version_id == published.id


@pytest.mark.asyncio
async def test_cannot_edit_published_version(version_service, evaluation_service, workspace):
    evaluation = await evaluation_service.create_evaluation(workspace.id, name="E1", owner_id="u1", category="prompt", organization_id="org-1")
    draft = await version_service.get_or_create_draft(evaluation.id, created_by="u1")
    await version_service.update_draft(draft.id, metric_keys=["accuracy"], target_config={"type": "prompt"})
    published = await version_service.publish_version(draft.id)
    with pytest.raises(ValidationError):
        await version_service.update_draft(published.id, metric_keys=["recall"])


@pytest.mark.asyncio
async def test_new_draft_seeds_from_published_version(version_service, evaluation_service, workspace):
    evaluation = await evaluation_service.create_evaluation(workspace.id, name="E1", owner_id="u1", category="prompt", organization_id="org-1")
    draft = await version_service.get_or_create_draft(evaluation.id, created_by="u1")
    await version_service.update_draft(draft.id, metric_keys=["accuracy"], target_config={"type": "prompt", "ref_id": "p1"}, pass_threshold=0.8)
    await version_service.publish_version(draft.id)

    draft2 = await version_service.get_or_create_draft(evaluation.id, created_by="u1")
    assert draft2.version_number == 2
    assert draft2.metric_keys == ["accuracy"]
    assert draft2.pass_threshold == 0.8


@pytest.mark.asyncio
async def test_deprecate_version_requires_published(version_service, evaluation_service, workspace):
    evaluation = await evaluation_service.create_evaluation(workspace.id, name="E1", owner_id="u1", category="prompt", organization_id="org-1")
    draft = await version_service.get_or_create_draft(evaluation.id, created_by="u1")
    with pytest.raises(ValidationError):
        await version_service.deprecate_version(draft.id)
