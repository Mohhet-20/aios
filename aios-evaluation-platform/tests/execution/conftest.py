import pytest

from eval_platform.datasets.dataset_service import DatasetService
from eval_platform.datasets.version_service import DatasetVersionService
from eval_platform.evaluation_core.evaluation_service import EvaluationService
from eval_platform.evaluation_core.version_service import EvaluationVersionService
from eval_platform.execution.evaluation_run_service import EvaluationRunService
from eval_platform.execution.executor import ReferenceTargetExecutor
from eval_platform.models.workspace import WorkspaceModel


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Exec Co", organization_id="org-1", slug="exec-co"))


@pytest.fixture
def dataset_service(repos):
    return DatasetService(repos)


@pytest.fixture
def dataset_version_service(repos):
    return DatasetVersionService(repos)


@pytest.fixture
def evaluation_service(repos):
    return EvaluationService(repos)


@pytest.fixture
def evaluation_version_service(repos):
    return EvaluationVersionService(repos)


@pytest.fixture
def run_service(repos):
    return EvaluationRunService(repos)


@pytest.fixture
def executor():
    return ReferenceTargetExecutor()


@pytest.fixture
async def ready_evaluation(workspace, dataset_service, dataset_version_service, evaluation_service, evaluation_version_service):
    """A published evaluation bound to a published 2-item dataset, with a
    `response_map` target_config keyed by the real dataset item ids so
    the ReferenceTargetExecutor can score it deterministically."""
    dataset = await dataset_service.create_dataset(workspace.id, name="QA Set", owner_id="u1", dataset_type="golden", organization_id="org-1")
    draft_version = await dataset_version_service.get_or_create_draft(dataset.id, created_by="u1")
    await dataset_version_service.add_items(draft_version.id, [
        {"input_data": {"q": "1+1"}, "expected_output": "2"},
        {"input_data": {"q": "2+2"}, "expected_output": "4"},
    ])
    published_dataset_version = await dataset_version_service.publish_version(draft_version.id)
    items = await dataset_version_service.list_items(published_dataset_version.id)
    response_map = {item.id: item.expected_output for item in items}

    evaluation = await evaluation_service.create_evaluation(workspace.id, name="Math Eval", owner_id="u1", category="prompt", organization_id="org-1")
    eval_draft = await evaluation_version_service.get_or_create_draft(evaluation.id, created_by="u1")
    await evaluation_version_service.update_draft(
        eval_draft.id, dataset_id=dataset.id, metric_keys=["accuracy"], pass_threshold=1.0,
        target_config={"type": "prompt", "response_map": response_map},
    )
    await evaluation_version_service.publish_version(eval_draft.id)
    return await evaluation_service.get_evaluation(evaluation.id)
