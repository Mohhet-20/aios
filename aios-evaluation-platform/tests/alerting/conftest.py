import pytest

from eval_platform.alerting.alert_service import AlertService
from eval_platform.alerting.evaluator import AlertEvaluator
from eval_platform.alerting.rule_service import AlertRuleService
from eval_platform.models.workspace import WorkspaceModel


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Alert Co", organization_id="org-1", slug="alert-co"))


@pytest.fixture
def rule_service(repos):
    return AlertRuleService(repos)


@pytest.fixture
def alert_service(repos):
    return AlertService(repos)


@pytest.fixture
def evaluator(repos):
    return AlertEvaluator(repos)
