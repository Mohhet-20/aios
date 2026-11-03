import pytest

from memory_platform.core.exceptions import InvalidTransitionError, ValidationError
from memory_platform.domain.enums import KnowledgeItemStatus
from memory_platform.knowledge.knowledge_service import KnowledgeService
from memory_platform.models.workspace import WorkspaceModel


async def _workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(id="ws-1", name="Acme", slug="acme", organization_id="org-1"))


async def _kb(svc, repos):
    await _workspace(repos)
    return await svc.create_knowledge_base(workspace_id="ws-1", name="Product KB", slug="product-kb", owner_id="user-1")


@pytest.mark.asyncio
async def test_create_knowledge_base_and_collection(repos):
    svc = KnowledgeService(repos)
    kb = await _kb(svc, repos)
    coll = await svc.create_collection(knowledge_base_id=kb.id, name="Onboarding", slug="onboarding")
    listed = await svc.list_collections(kb.id)
    assert [c.id for c in listed] == [coll.id]


@pytest.mark.asyncio
async def test_create_item_starts_draft_and_records_version(repos):
    svc = KnowledgeService(repos)
    kb = await _kb(svc, repos)
    item = await svc.create_item(workspace_id="ws-1", knowledge_base_id=kb.id, title="Setup Guide", content="Step 1...", owner_id="user-1")
    assert item.status == KnowledgeItemStatus.DRAFT.value
    versions = await svc.list_versions(item.id)
    assert len(versions) == 1
    assert versions[0].version_number == 1
    assert versions[0].content == "Step 1..."


@pytest.mark.asyncio
async def test_create_item_rejects_empty_content(repos):
    svc = KnowledgeService(repos)
    kb = await _kb(svc, repos)
    with pytest.raises(ValidationError):
        await svc.create_item(workspace_id="ws-1", knowledge_base_id=kb.id, title="Empty", content="   ", owner_id="user-1")


@pytest.mark.asyncio
async def test_update_content_bumps_version_and_appends_history(repos):
    svc = KnowledgeService(repos)
    kb = await _kb(svc, repos)
    item = await svc.create_item(workspace_id="ws-1", knowledge_base_id=kb.id, title="Guide", content="v1", owner_id="user-1")
    updated = await svc.update_content(item.id, content="v2", changed_by="user-1", change_note="fixed typo")
    assert updated.version == 2
    versions = await svc.list_versions(item.id)
    assert [v.version_number for v in versions] == [1, 2]
    assert versions[1].change_note == "fixed typo"


@pytest.mark.asyncio
async def test_full_review_publish_workflow(repos):
    svc = KnowledgeService(repos)
    kb = await _kb(svc, repos)
    item = await svc.create_item(workspace_id="ws-1", knowledge_base_id=kb.id, title="Guide", content="v1", owner_id="user-1")
    await svc.submit_for_review(item.id)
    published = await svc.approve_and_publish(item.id, reviewed_by="reviewer-1")
    assert published.status == KnowledgeItemStatus.PUBLISHED.value
    assert published.reviewed_by == "reviewer-1"
    assert published.published_at is not None


@pytest.mark.asyncio
async def test_publish_requires_in_review(repos):
    svc = KnowledgeService(repos)
    kb = await _kb(svc, repos)
    item = await svc.create_item(workspace_id="ws-1", knowledge_base_id=kb.id, title="Guide", content="v1", owner_id="user-1")
    with pytest.raises(InvalidTransitionError):
        await svc.approve_and_publish(item.id, reviewed_by="reviewer-1")


@pytest.mark.asyncio
async def test_reject_returns_to_draft(repos):
    svc = KnowledgeService(repos)
    kb = await _kb(svc, repos)
    item = await svc.create_item(workspace_id="ws-1", knowledge_base_id=kb.id, title="Guide", content="v1", owner_id="user-1")
    await svc.submit_for_review(item.id)
    rejected = await svc.reject(item.id, reviewed_by="reviewer-1")
    assert rejected.status == KnowledgeItemStatus.DRAFT.value
    assert rejected.reviewed_by == "reviewer-1"


@pytest.mark.asyncio
async def test_deprecate_then_archive(repos):
    svc = KnowledgeService(repos)
    kb = await _kb(svc, repos)
    item = await svc.create_item(workspace_id="ws-1", knowledge_base_id=kb.id, title="Guide", content="v1", owner_id="user-1")
    await svc.submit_for_review(item.id)
    await svc.approve_and_publish(item.id, reviewed_by="reviewer-1")
    deprecated = await svc.deprecate(item.id)
    assert deprecated.status == KnowledgeItemStatus.DEPRECATED.value
    archived = await svc.archive(item.id)
    assert archived.status == KnowledgeItemStatus.ARCHIVED.value


@pytest.mark.asyncio
async def test_search_finds_published_and_draft(repos):
    svc = KnowledgeService(repos)
    kb = await _kb(svc, repos)
    await svc.create_item(workspace_id="ws-1", knowledge_base_id=kb.id, title="Deploying to production", content="steps", owner_id="user-1")
    await svc.create_item(workspace_id="ws-1", knowledge_base_id=kb.id, title="Unrelated", content="other stuff", owner_id="user-1")
    results = await svc.search("ws-1", "deploying")
    assert len(results) == 1
    assert results[0].title == "Deploying to production"


@pytest.mark.asyncio
async def test_link_related_creates_kg_entities_and_relationship(repos):
    svc = KnowledgeService(repos)
    kb = await _kb(svc, repos)
    a = await svc.create_item(workspace_id="ws-1", knowledge_base_id=kb.id, title="A", content="content A", owner_id="user-1")
    b = await svc.create_item(workspace_id="ws-1", knowledge_base_id=kb.id, title="B", content="content B", owner_id="user-1")
    await svc.link_related(a.id, b.id, relation_type="related_to")
    related = await svc.list_related(a.id)
    assert len(related) == 1
    assert related[0].relation_type == "related_to"
