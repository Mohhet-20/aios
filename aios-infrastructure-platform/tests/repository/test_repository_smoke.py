"""One comprehensive smoke test: touches every repository through the
RepositoryRegistry to prove the schema, models, and repositories are
all wired together correctly."""
from __future__ import annotations

import pytest

from infra_platform.models.artifacts import ArtifactModel
from infra_platform.models.cicd import PipelineModel
from infra_platform.models.containers import ContainerImageModel
from infra_platform.models.experiments import ExperimentModel
from infra_platform.models.kubernetes import ClusterModel
from infra_platform.models.model_registry import ModelRegistryEntryModel

TENANT = "t1"


@pytest.mark.asyncio
async def test_repository_registry_smoke(repos):
    image = await repos.container_images.add(
        ContainerImageModel(tenant_id=TENANT, repository="aios/agent-platform", tag="1.0.0", status="building")
    )
    assert image.id is not None

    cluster = await repos.clusters.add(ClusterModel(tenant_id=TENANT, name="prod-us-east-1", provider="aws", region="us-east-1"))
    assert cluster.status == "provisioning"

    pipeline = await repos.pipelines.add(PipelineModel(tenant_id=TENANT, name="agent-platform-ci", repository="github.com/aios/agent-platform"))
    assert await repos.pipelines.get_by_name(TENANT, "agent-platform-ci") is not None

    await repos.model_registry_entries.add(ModelRegistryEntryModel(tenant_id=TENANT, name="fraud-classifier"))
    assert await repos.model_registry_entries.get_by_name(TENANT, "fraud-classifier") is not None

    await repos.experiments.add(ExperimentModel(tenant_id=TENANT, name="fraud-tuning-v3"))
    assert await repos.experiments.get_by_name(TENANT, "fraud-tuning-v3") is not None

    artifact = await repos.artifacts.add(ArtifactModel(tenant_id=TENANT, name="fraud-model-weights", artifact_type="model"))
    assert artifact.id is not None

    assert pipeline.id is not None
