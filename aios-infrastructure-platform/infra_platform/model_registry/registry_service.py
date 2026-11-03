"""Model Lifecycle Management: a registry entry per logical model
name, versions beneath it with a guarded development -> staging ->
production -> archived lifecycle, approval-gated promotion (an
approval record is always created for audit purposes; when
`model_promotion_requires_approval` is off it is auto-approved and
applied immediately rather than skipped), lineage edges, and
retention-based pruning of old archived versions."""
from __future__ import annotations


from infra_platform.config.settings import Settings, get_settings
from infra_platform.core.exceptions import (
    ModelRegistryError,
    ModelVersionNotFoundError,
    NotFoundError,
)
from infra_platform.domain.entities import ModelVersion as ModelVersionEntity
from infra_platform.domain.enums import ModelStage
from infra_platform.models.model_registry import (
    ModelApprovalModel,
    ModelLineageEdgeModel,
    ModelRegistryEntryModel,
    ModelVersionModel,
)
from infra_platform.repositories.registry import RepositoryRegistry
from infra_platform.clock import utc_now


class ModelRegistryService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def register_model(
        self, tenant_id: str, *, name: str, description: str | None = None, owner_id: str | None = None
    ) -> ModelRegistryEntryModel:
        existing = await self.repos.model_registry_entries.get_by_name(tenant_id, name)
        if existing is not None:
            raise ModelRegistryError(f"Model '{name}' already registered")
        model = ModelRegistryEntryModel(tenant_id=tenant_id, name=name, description=description, owner_id=owner_id)
        return await self.repos.model_registry_entries.add(model)

    async def get(self, tenant_id: str, model_id: str) -> ModelRegistryEntryModel:
        model = await self.repos.model_registry_entries.get(model_id)
        if model is None or model.tenant_id != tenant_id:
            raise NotFoundError(f"Model '{model_id}' not found")
        return model

    async def list_for_tenant(self, tenant_id: str) -> list[ModelRegistryEntryModel]:
        return await self.repos.model_registry_entries.list(filters={"tenant_id": tenant_id})


class ModelVersionService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def _get_version(self, tenant_id: str, model_version_id: str) -> ModelVersionModel:
        version = await self.repos.model_versions.get(model_version_id)
        if version is None or version.tenant_id != tenant_id:
            raise ModelVersionNotFoundError(f"ModelVersion '{model_version_id}' not found")
        return version

    async def create_version(
        self, tenant_id: str, model_id: str, *, source_run_id: str | None = None, artifact_id: str | None = None,
        metrics: dict | None = None, version_metadata: dict | None = None,
    ) -> ModelVersionModel:
        model = await self.repos.model_registry_entries.get(model_id)
        if model is None or model.tenant_id != tenant_id:
            raise NotFoundError(f"Model '{model_id}' not found")
        next_number = await self.repos.model_versions.get_latest_version_number(tenant_id, model_id) + 1
        version = ModelVersionModel(
            tenant_id=tenant_id, model_id=model_id, version_number=next_number, stage=ModelStage.DEVELOPMENT.value,
            source_run_id=source_run_id, artifact_id=artifact_id, metrics=metrics or {}, version_metadata=version_metadata or {},
        )
        return await self.repos.model_versions.add(version)

    async def _apply_promotion(self, tenant_id: str, version: ModelVersionModel, target: ModelStage) -> ModelVersionModel:
        entity = ModelVersionEntity(id=version.id, stage=ModelStage(version.stage))
        if target == ModelStage.STAGING:
            entity.promote_to_staging()
        elif target == ModelStage.PRODUCTION:
            entity.promote_to_production()
        elif target == ModelStage.ARCHIVED:
            entity.archive()
        else:
            raise ModelRegistryError(f"Cannot promote directly to '{target.value}'")
        version.stage = entity.stage.value
        version = await self.repos.model_versions.update(version)

        if target == ModelStage.PRODUCTION:
            model = await self.repos.model_registry_entries.get(version.model_id)
            if model is not None and model.tenant_id == tenant_id:
                model.current_production_version_id = version.id
                await self.repos.model_registry_entries.update(model)
        return version

    async def request_promotion(
        self, tenant_id: str, model_version_id: str, *, requested_stage: str, reviewer_id: str | None = None
    ) -> ModelApprovalModel:
        await self._get_version(tenant_id, model_version_id)
        try:
            target = ModelStage(requested_stage)
        except ValueError as exc:
            raise ModelRegistryError(f"Unknown model stage '{requested_stage}'") from exc

        approval = await self.repos.model_approvals.add(
            ModelApprovalModel(
                tenant_id=tenant_id, model_version_id=model_version_id, status="pending",
                requested_stage=target.value, reviewer_id=reviewer_id,
            )
        )
        if not self.settings.model_promotion_requires_approval:
            approval = await self.decide_approval(tenant_id, approval.id, approved=True, reviewer_id=reviewer_id)
        return approval

    async def decide_approval(
        self, tenant_id: str, approval_id: str, *, approved: bool, reviewer_id: str | None = None, comments: str | None = None
    ) -> ModelApprovalModel:
        approval = await self.repos.model_approvals.get_or_404(approval_id)
        if approval.tenant_id != tenant_id:
            raise ModelRegistryError(f"Approval '{approval_id}' not found")
        if approval.status != "pending":
            raise ModelRegistryError(f"Approval '{approval_id}' already decided (status={approval.status})")

        approval.status = "approved" if approved else "rejected"
        approval.reviewer_id = reviewer_id or approval.reviewer_id
        approval.comments = comments
        approval.decided_at = utc_now()
        approval = await self.repos.model_approvals.update(approval)

        if approved:
            version = await self._get_version(tenant_id, approval.model_version_id)
            target = ModelStage(approval.requested_stage)
            await self._apply_promotion(tenant_id, version, target)
        return approval

    async def archive_version(self, tenant_id: str, model_version_id: str) -> ModelVersionModel:
        version = await self._get_version(tenant_id, model_version_id)
        return await self._apply_promotion(tenant_id, version, ModelStage.ARCHIVED)

    async def list_for_model(self, tenant_id: str, model_id: str) -> list[ModelVersionModel]:
        return await self.repos.model_versions.list_for_model(tenant_id, model_id)

    async def list_by_stage(self, tenant_id: str, model_id: str, stage: str) -> list[ModelVersionModel]:
        return await self.repos.model_versions.list_by_stage(tenant_id, model_id, stage)

    async def prune_old_versions(self, tenant_id: str, model_id: str) -> int:
        """Hard-deletes archived versions beyond `model_version_retention_count`,
        oldest first — the retention-pruning pattern shared with the
        Container Image Registry's `prune_old_versions`."""
        versions = await self.repos.model_versions.list_for_model(tenant_id, model_id)
        archived = sorted(
            (v for v in versions if v.stage == ModelStage.ARCHIVED.value), key=lambda v: v.version_number, reverse=True
        )
        retain = self.settings.model_version_retention_count
        pruned = 0
        for stale in archived[retain:]:
            await self.repos.model_versions.delete(stale)
            pruned += 1
        return pruned


class ModelLineageService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def record_lineage(
        self, tenant_id: str, model_version_id: str, *, parent_type: str, parent_ref_id: str
    ) -> ModelLineageEdgeModel:
        edge = ModelLineageEdgeModel(
            tenant_id=tenant_id, model_version_id=model_version_id, parent_type=parent_type, parent_ref_id=parent_ref_id
        )
        return await self.repos.model_lineage_edges.add(edge)

    async def list_for_version(self, tenant_id: str, model_version_id: str) -> list[ModelLineageEdgeModel]:
        return await self.repos.model_lineage_edges.list_for_version(tenant_id, model_version_id)
