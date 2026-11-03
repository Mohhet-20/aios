import pytest

from eval_platform.core.exceptions import ValidationError
from eval_platform.core.pagination import PaginationParams
from eval_platform.domain.enums import EvaluationStatus


@pytest.mark.asyncio
async def test_create_evaluation_defaults_to_draft(evaluation_service, workspace):
    evaluation = await evaluation_service.create_evaluation(
        workspace.id, name="Groundedness Check", owner_id="u1", category="groundedness", organization_id="org-1",
    )
    assert evaluation.status == EvaluationStatus.DRAFT.value
    assert evaluation.slug == "groundedness-check"


@pytest.mark.asyncio
async def test_create_evaluation_duplicate_slug_raises(evaluation_service, workspace):
    await evaluation_service.create_evaluation(workspace.id, name="Dup", owner_id="u1", category="prompt", organization_id="org-1")
    with pytest.raises(ValidationError):
        await evaluation_service.create_evaluation(workspace.id, name="Dup", owner_id="u1", category="prompt", organization_id="org-1")


@pytest.mark.asyncio
async def test_update_evaluation_rejects_unknown_field(evaluation_service, workspace):
    evaluation = await evaluation_service.create_evaluation(workspace.id, name="E1", owner_id="u1", category="prompt", organization_id="org-1")
    with pytest.raises(ValidationError):
        await evaluation_service.update_evaluation(evaluation.id, status="active")


@pytest.mark.asyncio
async def test_update_evaluation_allowed_fields(evaluation_service, workspace):
    evaluation = await evaluation_service.create_evaluation(workspace.id, name="E1", owner_id="u1", category="prompt", organization_id="org-1")
    updated = await evaluation_service.update_evaluation(evaluation.id, description="new desc", tags=["a", "b"])
    assert updated.description == "new desc"
    assert updated.tags == ["a", "b"]


@pytest.mark.asyncio
async def test_list_evaluations_paginated(evaluation_service, workspace):
    for i in range(3):
        await evaluation_service.create_evaluation(workspace.id, name=f"E{i}", owner_id="u1", category="prompt", organization_id="org-1")
    page = await evaluation_service.list_evaluations(workspace.id, PaginationParams(page=1, page_size=2))
    assert page.total == 3
    assert len(page.items) == 2


@pytest.mark.asyncio
async def test_search_evaluations(evaluation_service, workspace):
    await evaluation_service.create_evaluation(workspace.id, name="Faithfulness Suite", owner_id="u1", category="groundedness", organization_id="org-1")
    await evaluation_service.create_evaluation(workspace.id, name="Safety Suite", owner_id="u1", category="safety", organization_id="org-1")
    results = await evaluation_service.search_evaluations(workspace.id, "faithfulness")
    assert len(results) == 1
    assert results[0].name == "Faithfulness Suite"


@pytest.mark.asyncio
async def test_delete_evaluation_soft_deletes(evaluation_service, workspace):
    evaluation = await evaluation_service.create_evaluation(workspace.id, name="ToDelete", owner_id="u1", category="prompt", organization_id="org-1")
    await evaluation_service.delete_evaluation(evaluation.id)
    listed = await evaluation_service.list_evaluations(workspace.id, PaginationParams())
    assert listed.total == 0
