import pytest

from eval_platform.benchmarking.benchmark_service import BenchmarkService
from eval_platform.benchmarking.run_service import BenchmarkRunService
from eval_platform.datasets.dataset_service import DatasetService
from eval_platform.datasets.version_service import DatasetVersionService
from eval_platform.execution.executor import ReferenceTargetExecutor
from eval_platform.models.workspace import WorkspaceModel


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Bench Co", organization_id="org-1", slug="bench-co"))


@pytest.fixture
def dataset_service(repos):
    return DatasetService(repos)


@pytest.fixture
def dataset_version_service(repos):
    return DatasetVersionService(repos)


@pytest.fixture
def benchmark_service(repos):
    return BenchmarkService(repos)


@pytest.fixture
def run_service(repos):
    return BenchmarkRunService(repos)


@pytest.fixture
def executor():
    return ReferenceTargetExecutor()


@pytest.fixture
async def ready_dataset(workspace, dataset_service, dataset_version_service):
    dataset = await dataset_service.create_dataset(workspace.id, name="Bench Set", owner_id="u1", dataset_type="golden", organization_id="org-1")
    draft = await dataset_version_service.get_or_create_draft(dataset.id, created_by="u1")
    await dataset_version_service.add_items(draft.id, [
        {"input_data": {"q": "1+1"}, "expected_output": "2"},
        {"input_data": {"q": "2+2"}, "expected_output": "4"},
    ])
    await dataset_version_service.publish_version(draft.id)
    return await dataset_service.get_dataset(dataset.id)


@pytest.fixture
async def ready_benchmark(workspace, benchmark_service, ready_dataset):
    return await benchmark_service.create_benchmark(
        workspace.id, name="Model Shootout", owner_id="u1", benchmark_type="model", mode="ab_test",
        organization_id="org-1", dataset_id=ready_dataset.id, metric_keys=["accuracy"],
    )
