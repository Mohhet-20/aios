import pytest

from eval_platform.datasets.dataset_service import DatasetService
from eval_platform.datasets.version_service import DatasetVersionService
from eval_platform.models.workspace import WorkspaceModel


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Dataset Co", organization_id="org-1", slug="dataset-co"))


@pytest.fixture
async def other_workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Dataset Co 2", organization_id="org-1", slug="dataset-co-2"))


@pytest.fixture
def dataset_service(repos):
    return DatasetService(repos)


@pytest.fixture
def version_service(repos):
    return DatasetVersionService(repos)
