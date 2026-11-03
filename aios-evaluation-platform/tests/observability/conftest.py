import pytest

from eval_platform.models.workspace import WorkspaceModel
from eval_platform.observability.ingestion_service import ObservabilityIngestionService
from eval_platform.observability.monitoring_service import ObservabilityMonitoringService


@pytest.fixture
async def workspace(repos):
    return await repos.workspaces.add(WorkspaceModel(name="Observability Co", organization_id="org-1", slug="observability-co"))


@pytest.fixture
def ingestion_service(repos):
    return ObservabilityIngestionService(repos)


@pytest.fixture
def monitoring_service(repos):
    return ObservabilityMonitoringService(repos)
