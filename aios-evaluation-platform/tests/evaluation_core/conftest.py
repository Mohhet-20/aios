import pytest

from eval_platform.evaluation_core.evaluation_service import EvaluationService
from eval_platform.evaluation_core.version_service import EvaluationVersionService
from eval_platform.models.workspace import WorkspaceModel


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Eval Core Co", organization_id="org-1", slug="eval-core-co"))


@pytest.fixture
def evaluation_service(repos):
    return EvaluationService(repos)


@pytest.fixture
def version_service(repos):
    return EvaluationVersionService(repos)
