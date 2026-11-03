import pytest

from eval_platform.core.exceptions import DatasetError


@pytest.mark.asyncio
async def test_create_dataset_defaults_to_draft(dataset_service, workspace):
    dataset = await dataset_service.create_dataset(
        workspace.id, name="Golden QA Set", owner_id="u1", dataset_type="golden", organization_id="org-1",
    )
    assert dataset.status == "draft"
    assert dataset.slug == "golden-qa-set"


@pytest.mark.asyncio
async def test_create_dataset_duplicate_slug_raises(dataset_service, workspace):
    await dataset_service.create_dataset(workspace.id, name="D1", owner_id="u1", dataset_type="golden", organization_id="org-1")
    with pytest.raises(DatasetError):
        await dataset_service.create_dataset(workspace.id, name="D1", owner_id="u1", dataset_type="golden", organization_id="org-1")


@pytest.mark.asyncio
async def test_update_dataset_rejects_unknown_field(dataset_service, workspace):
    dataset = await dataset_service.create_dataset(workspace.id, name="D1", owner_id="u1", dataset_type="golden", organization_id="org-1")
    with pytest.raises(DatasetError):
        await dataset_service.update_dataset(dataset.id, dataset_type="synthetic")


@pytest.mark.asyncio
async def test_update_dataset_allowed_fields(dataset_service, workspace):
    dataset = await dataset_service.create_dataset(workspace.id, name="D1", owner_id="u1", dataset_type="golden", organization_id="org-1")
    updated = await dataset_service.update_dataset(dataset.id, description="updated desc", tags=["qa"])
    assert updated.description == "updated desc"
    assert updated.tags == ["qa"]


@pytest.mark.asyncio
async def test_list_datasets_paginated(dataset_service, workspace):
    from eval_platform.core.pagination import PaginationParams

    for i in range(3):
        await dataset_service.create_dataset(workspace.id, name=f"D{i}", owner_id="u1", dataset_type="golden", organization_id="org-1")
    page = await dataset_service.list_datasets(workspace.id, PaginationParams(page=1, page_size=10))
    assert page.total == 3


@pytest.mark.asyncio
async def test_delete_dataset_soft_deletes(dataset_service, workspace):
    dataset = await dataset_service.create_dataset(workspace.id, name="D1", owner_id="u1", dataset_type="golden", organization_id="org-1")
    await dataset_service.delete_dataset(dataset.id)
    from eval_platform.core.pagination import PaginationParams
    page = await dataset_service.list_datasets(workspace.id, PaginationParams(page=1, page_size=10))
    assert page.total == 0


@pytest.mark.asyncio
async def test_share_with_workspace_makes_it_visible(dataset_service, workspace, other_workspace):
    dataset = await dataset_service.create_dataset(workspace.id, name="Shared", owner_id="u1", dataset_type="golden", organization_id="org-1")
    await dataset_service.share_with_workspace(dataset.id, other_workspace.id)
    shared = await dataset_service.list_shared_with_workspace(other_workspace.id, "org-1")
    assert len(shared) == 1
    assert shared[0].id == dataset.id


@pytest.mark.asyncio
async def test_lineage_parent_dataset_tracked(dataset_service, workspace):
    parent = await dataset_service.create_dataset(workspace.id, name="Prod Samples", owner_id="u1", dataset_type="production_sample", organization_id="org-1")
    child = await dataset_service.create_dataset(
        workspace.id, name="Regression Set", owner_id="u1", dataset_type="regression", organization_id="org-1",
        lineage_parent_dataset_id=parent.id,
    )
    assert child.lineage_parent_dataset_id == parent.id
