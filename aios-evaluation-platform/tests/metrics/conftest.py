import pytest

from eval_platform.metrics.scorer import MetricScorer
from eval_platform.models.workspace import WorkspaceModel


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Metrics Co", organization_id="org-1", slug="metrics-co"))


@pytest.fixture
def scorer(repos):
    return MetricScorer(repos)
