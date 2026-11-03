import pytest

from eval_platform.analytics.improvement_loop import ImprovementLoopService
from eval_platform.analytics.recommendation_service import RecommendationService
from eval_platform.analytics.snapshot_service import AnalyticsSnapshotService
from eval_platform.datasets.dataset_service import DatasetService
from eval_platform.datasets.version_service import DatasetVersionService
from eval_platform.evaluation_core.evaluation_service import EvaluationService
from eval_platform.evaluation_core.version_service import EvaluationVersionService
from eval_platform.execution.evaluation_run_service import EvaluationRunService
from eval_platform.execution.executor import ReferenceTargetExecutor
from eval_platform.models.workspace import WorkspaceModel
from eval_platform.observability.ingestion_service import ObservabilityIngestionService


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Analytics Co", organization_id="org-1", slug="analytics-co"))


@pytest.fixture
def snapshot_service(repos):
    return AnalyticsSnapshotService(repos)


@pytest.fixture
def recommendation_service(repos):
    return RecommendationService(repos)


@pytest.fixture
def improvement_loop(repos):
    return ImprovementLoopService(repos)


@pytest.fixture
def ingestion_service(repos):
    return ObservabilityIngestionService(repos)


@pytest.fixture
def executor():
    return ReferenceTargetExecutor()


@pytest.fixture
async def ready_evaluation(repos, workspace):
    """A published evaluation bound to a 1-item dataset with a
    'response_map' target_config, for producing real EvaluationRun rows."""
    dataset_service = DatasetService(repos)
    dataset_version_service = DatasetVersionService(repos)
    dataset = await dataset_service.create_dataset(workspace.id, name="Analytics Set", owner_id="u1", dataset_type="golden", organization_id="org-1")
    draft = await dataset_version_service.get_or_create_draft(dataset.id, created_by="u1")
    await dataset_version_service.add_items(draft.id, [{"input_data": {"q": "1+1"}, "expected_output": "2"}])
    published = await dataset_version_service.publish_version(draft.id)
    items = await dataset_version_service.list_items(published.id)
    item = items[0]

    evaluation_service = EvaluationService(repos)
    evaluation_version_service = EvaluationVersionService(repos)
    evaluation = await evaluation_service.create_evaluation(workspace.id, name="Analytics Eval", owner_id="u1", category="prompt", organization_id="org-1")
    eval_draft = await evaluation_version_service.get_or_create_draft(evaluation.id, created_by="u1")
    await evaluation_version_service.update_draft(
        eval_draft.id, dataset_id=dataset.id, metric_keys=["accuracy"], pass_threshold=1.0,
        target_config={"type": "prompt", "response_map": {item.id: "2"}},
    )
    await evaluation_version_service.publish_version(eval_draft.id)
    return await evaluation_service.get_evaluation(evaluation.id)


@pytest.fixture
def run_service(repos):
    return EvaluationRunService(repos)
