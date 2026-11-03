import pytest

from eval_platform.hallucination.service import HallucinationDetectionService
from eval_platform.models.workspace import WorkspaceModel


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Hallucination Co", organization_id="org-1", slug="hallucination-co"))


@pytest.fixture
def service(repos):
    return HallucinationDetectionService(repos)
