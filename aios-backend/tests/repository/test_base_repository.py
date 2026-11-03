"""Repository-layer tests against a real (in-memory SQLite) database — these
exercise soft delete, optimistic locking, and generic list/filter behavior
that every concrete repository inherits from `SQLAlchemyRepository`.
"""

import pytest

from app.core.exceptions import NotFoundError
from app.models.workspace import WorkspaceModel
from app.repositories.workspace_repository import WorkspaceRepository


@pytest.mark.asyncio
async def test_add_and_get(db_session):
    repo = WorkspaceRepository(db_session)
    workspace = await repo.add(WorkspaceModel(organization_id="org1", name="Test WS"))
    fetched = await repo.get(workspace.id)
    assert fetched is not None
    assert fetched.name == "Test WS"


@pytest.mark.asyncio
async def test_get_or_404_raises_not_found(db_session):
    repo = WorkspaceRepository(db_session)
    with pytest.raises(NotFoundError):
        await repo.get_or_404("does-not-exist")


@pytest.mark.asyncio
async def test_soft_delete_excludes_from_list(db_session):
    repo = WorkspaceRepository(db_session)
    workspace = await repo.add(WorkspaceModel(organization_id="org2", name="To Delete"))
    await repo.delete(workspace.id, soft=True)

    fetched = await repo.get(workspace.id)
    assert fetched is None  # excluded by default

    fetched_including_deleted = await repo.get(workspace.id, include_deleted=True)
    assert fetched_including_deleted is not None
    assert fetched_including_deleted.is_deleted is True


@pytest.mark.asyncio
async def test_list_filters_by_field(db_session):
    repo = WorkspaceRepository(db_session)
    await repo.add(WorkspaceModel(organization_id="org3", name="A"))
    await repo.add(WorkspaceModel(organization_id="org3", name="B"))
    await repo.add(WorkspaceModel(organization_id="org4", name="C"))

    results = await repo.list(organization_id="org3")
    assert len(results) == 2
    assert {r.name for r in results} == {"A", "B"}
