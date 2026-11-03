"""Deployment Orchestration: one row per deployment attempt across the
9 declared target types (cloud, on-prem, hybrid, edge, multi-region,
multi-cluster, multi-tenant, air-gapped, offline), guarded through the
shared queued -> in_progress -> succeeded/failed -> rolled_back job
lifecycle via the ephemeral `Deployment` domain entity.

Deliberately does not cross-validate that `release_id`/`environment_id`
point at real rows — this module is intentionally decoupled from
Release Management and Environment Management so all three can evolve
independently; a caller (or the REST layer, or a future orchestration
workflow) is responsible for resolving those references first if it
cares. This mirrors the same "loose FK, no forced cross-module
dependency" choice documented elsewhere in this platform family (e.g.
docs_platform's search/assistant modules)."""
from __future__ import annotations

from release_platform.config.settings import get_settings
from release_platform.core.exceptions import DeploymentNotFoundError, UnsupportedDeploymentTargetError
from release_platform.domain.entities import Deployment
from release_platform.domain.enums import JobStatus
from release_platform.models.deployment import DeploymentModel
from release_platform.repositories.registry import RepositoryRegistry


class DeploymentService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos
        self.settings = get_settings()

    async def get_or_404(self, tenant_id: str, deployment_id: str) -> DeploymentModel:
        deployment = await self.repos.deployments.get_or_404(deployment_id)
        if deployment.tenant_id != tenant_id:
            raise DeploymentNotFoundError(f"Deployment '{deployment_id}' not found for tenant '{tenant_id}'")
        return deployment

    async def create_deployment(
        self, tenant_id: str, *, release_id: str, environment_id: str, target_type: str, initiated_by: str | None = None
    ) -> DeploymentModel:
        if target_type not in self.settings.deployment_targets:
            raise UnsupportedDeploymentTargetError(f"Unsupported deployment target '{target_type}'")
        deployment = DeploymentModel(
            tenant_id=tenant_id, release_id=release_id, environment_id=environment_id,
            target_type=target_type, status=JobStatus.QUEUED.value, initiated_by=initiated_by,
        )
        return await self.repos.deployments.add(deployment)

    def _to_entity(self, deployment: DeploymentModel) -> Deployment:
        return Deployment(
            id=deployment.id, tenant_id=deployment.tenant_id, release_id=deployment.release_id,
            environment_id=deployment.environment_id, target_type=deployment.target_type, status=JobStatus(deployment.status),
        )

    async def start(self, tenant_id: str, deployment_id: str) -> DeploymentModel:
        deployment = await self.get_or_404(tenant_id, deployment_id)
        entity = self._to_entity(deployment)
        entity.start()
        deployment.status = entity.status.value
        deployment.started_at = entity.started_at
        return deployment

    async def succeed(self, tenant_id: str, deployment_id: str) -> DeploymentModel:
        deployment = await self.get_or_404(tenant_id, deployment_id)
        entity = self._to_entity(deployment)
        entity.succeed()
        deployment.status = entity.status.value
        deployment.finished_at = entity.finished_at
        return deployment

    async def fail(self, tenant_id: str, deployment_id: str, *, reason: str) -> DeploymentModel:
        deployment = await self.get_or_404(tenant_id, deployment_id)
        entity = self._to_entity(deployment)
        entity.fail(reason=reason)
        deployment.status = entity.status.value
        deployment.finished_at = entity.finished_at
        deployment.failure_reason = entity.failure_reason
        return deployment

    async def mark_rolled_back(self, tenant_id: str, deployment_id: str) -> DeploymentModel:
        deployment = await self.get_or_404(tenant_id, deployment_id)
        entity = self._to_entity(deployment)
        entity.mark_rolled_back()
        deployment.status = entity.status.value
        return deployment

    async def list_deployments(self, tenant_id: str, *, environment_id: str | None = None, status: str | None = None) -> list[DeploymentModel]:
        return await self.repos.deployments.list_for_tenant(tenant_id, environment_id=environment_id, status=status)
