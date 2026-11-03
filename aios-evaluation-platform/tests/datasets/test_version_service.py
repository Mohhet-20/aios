import pytest

from eval_platform.core.exceptions import DatasetError, DatasetVersionError


@pytest.mark.asyncio
async def test_get_or_create_draft_creates_first_version(version_service, dataset_service, workspace):
    dataset = await dataset_service.create_dataset(workspace.id, name="D1", owner_id="u1", dataset_type="golden", organization_id="org-1")
    draft = await version_service.get_or_create_draft(dataset.id, created_by="u1")
    assert draft.version_number == 1
    assert draft.status == "draft"
    assert draft.item_count == 0


@pytest.mark.asyncio
async def test_get_or_create_draft_is_idempotent(version_service, dataset_service, workspace):
    dataset = await dataset_service.create_dataset(workspace.id, name="D1", owner_id="u1", dataset_type="golden", organization_id="org-1")
    d1 = await version_service.get_or_create_draft(dataset.id, created_by="u1")
    d2 = await version_service.get_or_create_draft(dataset.id, created_by="u1")
    assert d1.id == d2.id


@pytest.mark.asyncio
async def test_add_items_updates_count(version_service, dataset_service, workspace):
    dataset = await dataset_service.create_dataset(workspace.id, name="D1", owner_id="u1", dataset_type="golden", organization_id="org-1")
    draft = await version_service.get_or_create_draft(dataset.id, created_by="u1")
    updated = await version_service.add_items(draft.id, [
        {"input_data": {"q": "1+1"}, "expected_output": {"a": "2"}},
        {"input_data": {"q": "2+2"}, "expected_output": {"a": "4"}},
    ])
    assert updated.item_count == 2
    items = await version_service.list_items(draft.id)
    assert len(items) == 2


@pytest.mark.asyncio
async def test_add_items_rejects_empty_batch(version_service, dataset_service, workspace):
    dataset = await dataset_service.create_dataset(workspace.id, name="D1", owner_id="u1", dataset_type="golden", organization_id="org-1")
    draft = await version_service.get_or_create_draft(dataset.id, created_by="u1")
    with pytest.raises(DatasetError):
        await version_service.add_items(draft.id, [])


@pytest.mark.asyncio
async def test_add_items_rejects_batch_over_limit(version_service, dataset_service, workspace, monkeypatch):
    from eval_platform.config import settings as settings_module
    settings_module.get_settings.cache_clear()
    monkeypatch.setenv("MAX_DATASET_BATCH_SIZE", "2")
    settings_module.get_settings.cache_clear()

    dataset = await dataset_service.create_dataset(workspace.id, name="D1", owner_id="u1", dataset_type="golden", organization_id="org-1")
    draft = await version_service.get_or_create_draft(dataset.id, created_by="u1")
    with pytest.raises(DatasetError):
        await version_service.add_items(draft.id, [{"input_data": {}}, {"input_data": {}}, {"input_data": {}}])

    settings_module.get_settings.cache_clear()


@pytest.mark.asyncio
async def test_publish_requires_at_least_one_item(version_service, dataset_service, workspace):
    dataset = await dataset_service.create_dataset(workspace.id, name="D1", owner_id="u1", dataset_type="golden", organization_id="org-1")
    draft = await version_service.get_or_create_draft(dataset.id, created_by="u1")
    with pytest.raises(DatasetVersionError):
        await version_service.publish_version(draft.id)


@pytest.mark.asyncio
async def test_publish_activates_dataset(version_service, dataset_service, workspace):
    dataset = await dataset_service.create_dataset(workspace.id, name="D1", owner_id="u1", dataset_type="golden", organization_id="org-1")
    draft = await version_service.get_or_create_draft(dataset.id, created_by="u1")
    await version_service.add_items(draft.id, [{"input_data": {"q": "1"}, "expected_output": {"a": "1"}}])
    published = await version_service.publish_version(draft.id)
    assert published.status == "published"

    refreshed = await dataset_service.get_dataset(dataset.id)
    assert refreshed.status == "published"
    assert refreshed.current_version_id == published.id


@pytest.mark.asyncio
async def test_cannot_edit_published_version(version_service, dataset_service, workspace):
    dataset = await dataset_service.create_dataset(workspace.id, name="D1", owner_id="u1", dataset_type="golden", organization_id="org-1")
    draft = await version_service.get_or_create_draft(dataset.id, created_by="u1")
    await version_service.add_items(draft.id, [{"input_data": {"q": "1"}, "expected_output": {"a": "1"}}])
    published = await version_service.publish_version(draft.id)
    with pytest.raises(DatasetVersionError):
        await version_service.add_items(published.id, [{"input_data": {"q": "2"}}])


@pytest.mark.asyncio
async def test_new_draft_seeds_items_from_published_version_and_republishes(version_service, dataset_service, workspace):
    dataset = await dataset_service.create_dataset(workspace.id, name="D1", owner_id="u1", dataset_type="golden", organization_id="org-1")
    draft = await version_service.get_or_create_draft(dataset.id, created_by="u1")
    await version_service.add_items(draft.id, [{"input_data": {"q": "1"}, "expected_output": {"a": "1"}}])
    await version_service.publish_version(draft.id)

    draft2 = await version_service.get_or_create_draft(dataset.id, created_by="u1")
    assert draft2.version_number == 2
    assert draft2.item_count == 1

    await version_service.add_items(draft2.id, [{"input_data": {"q": "2"}, "expected_output": {"a": "2"}}])
    published2 = await version_service.publish_version(draft2.id)
    assert published2.item_count == 2

    refreshed = await dataset_service.get_dataset(dataset.id)
    assert refreshed.status == "published"
    assert refreshed.current_version_id == published2.id


@pytest.mark.asyncio
async def test_deprecate_version_requires_published(version_service, dataset_service, workspace):
    dataset = await dataset_service.create_dataset(workspace.id, name="D1", owner_id="u1", dataset_type="golden", organization_id="org-1")
    draft = await version_service.get_or_create_draft(dataset.id, created_by="u1")
    with pytest.raises(DatasetVersionError):
        await version_service.deprecate_version(draft.id)
