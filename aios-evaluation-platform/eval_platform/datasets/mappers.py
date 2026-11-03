"""ORM <-> domain-aggregate bridge for Dataset, mirroring
evaluation_core's mappers.py pattern."""
from __future__ import annotations

from eval_platform.domain.entities import Dataset
from eval_platform.domain.enums import DatasetStatus
from eval_platform.models.dataset import DatasetModel


def dataset_to_domain(model: DatasetModel) -> Dataset:
    return Dataset(
        id=model.id, workspace_id=model.workspace_id, organization_id=model.organization_id, name=model.name,
        slug=model.slug, owner_id=model.owner_id, dataset_type=model.dataset_type, description=model.description,
        tags=list(model.tags or []), status=DatasetStatus(model.status), current_version_id=model.current_version_id,
        lineage_parent_dataset_id=model.lineage_parent_dataset_id, dataset_metadata=dict(model.dataset_metadata or {}),
    )


def apply_dataset_domain_to_model(entity: Dataset, model: DatasetModel) -> None:
    model.status = entity.status.value
    model.current_version_id = entity.current_version_id
    model.tags = entity.tags
    model.dataset_metadata = entity.dataset_metadata
