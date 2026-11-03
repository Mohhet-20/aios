"""Prompt Deployment system: promotes prompt versions across physical
environments (development/testing/staging/production), independent of
the version-control branch concept in prompt_engine.versioning_service
(EXPERIMENTAL/STABLE/PRODUCTION is "how proven is this version"; a
deployment environment is "where does it actually run"). Supports
approval-gated promotion, canary rollout, rollback, and per-environment
config.
"""
from __future__ import annotations


from prompt_platform.core.exceptions import (
    ApprovalRequiredError,
    DeploymentError,
    InvalidTransitionError,
    ValidationError,
)
from prompt_platform.domain.enums import DeploymentEnvironment, DeploymentStatus, VersionStatus
from prompt_platform.models.deployment import DeploymentEnvironmentConfigModel, DeploymentModel
from prompt_platform.repositories.registry import RepositoryRegistry
from prompt_platform.clock import utc_now

# Environments where going live requires an explicit human approval step.
# Development/testing are low-stakes iteration lanes and auto-approve.
_DEFAULT_APPROVAL_REQUIRED_ENVIRONMENTS = {DeploymentEnvironment.STAGING, DeploymentEnvironment.PRODUCTION}


class DeploymentService:
    def __init__(
        self, repos: RepositoryRegistry, *,
        approval_required_environments: set[DeploymentEnvironment] | None = None,
        min_production_eval_score: float = 85.0,
    ):
        self.repos = repos
        self.approval_required_environments = approval_required_environments or _DEFAULT_APPROVAL_REQUIRED_ENVIRONMENTS
        self.min_production_eval_score = min_production_eval_score

    # -- requesting a deployment ---------------------------------------------

    async def request_deployment(
        self, prompt_id: str, version_id: str, environment: DeploymentEnvironment, *,
        requested_by: str, canary_percent: float = 100.0, notes: str | None = None,
    ) -> DeploymentModel:
        version = await self.repos.versions.get_or_404(version_id)
        if not (0.0 < canary_percent <= 100.0):
            raise ValidationError("canary_percent must be in (0, 100]")

        requires_approval = environment in self.approval_required_environments
        if requires_approval and version.status != VersionStatus.APPROVED.value:
            raise ApprovalRequiredError(
                f"Version '{version_id}' must be APPROVED before deploying to '{environment.value}' "
                f"(current status: '{version.status}')"
            )
        if environment == DeploymentEnvironment.PRODUCTION and (version.eval_score or 0.0) < self.min_production_eval_score:
            raise ApprovalRequiredError(
                f"Version '{version_id}' eval_score {version.eval_score} is below the production "
                f"gate of {self.min_production_eval_score}"
            )

        deployment = DeploymentModel(
            prompt_id=prompt_id, version_id=version_id, environment=environment.value,
            status=(DeploymentStatus.PENDING_APPROVAL if requires_approval else DeploymentStatus.APPROVED).value,
            canary_percent=canary_percent, requested_by=requested_by, notes=notes,
        )
        if not requires_approval:
            deployment.approved_by = requested_by
            deployment.approved_at = utc_now()
        return await self.repos.deployments.add(deployment)

    # -- approval workflow -----------------------------------------------------

    async def approve(self, deployment_id: str, *, approved_by: str) -> DeploymentModel:
        deployment = await self.repos.deployments.get_or_404(deployment_id)
        if deployment.status != DeploymentStatus.PENDING_APPROVAL.value:
            raise InvalidTransitionError(f"Cannot approve a deployment in status '{deployment.status}'")
        deployment.status = DeploymentStatus.APPROVED.value
        deployment.approved_by = approved_by
        deployment.approved_at = utc_now()
        return await self.repos.deployments.update(deployment)

    async def reject(self, deployment_id: str, *, actor_id: str, reason: str | None = None) -> DeploymentModel:
        deployment = await self.repos.deployments.get_or_404(deployment_id)
        if deployment.status != DeploymentStatus.PENDING_APPROVAL.value:
            raise InvalidTransitionError(f"Cannot reject a deployment in status '{deployment.status}'")
        deployment.status = DeploymentStatus.REJECTED.value
        deployment.notes = f"{deployment.notes or ''}\nRejected by {actor_id}: {reason}".strip()
        return await self.repos.deployments.update(deployment)

    # -- go-live / canary ------------------------------------------------------

    async def deploy(self, deployment_id: str, *, actor_id: str) -> DeploymentModel:
        deployment = await self.repos.deployments.get_or_404(deployment_id)
        if deployment.status != DeploymentStatus.APPROVED.value:
            raise InvalidTransitionError(f"Cannot deploy a deployment in status '{deployment.status}' — it must be APPROVED first")
        deployment.status = DeploymentStatus.DEPLOYED.value
        deployment.deployed_at = utc_now()
        return await self.repos.deployments.update(deployment)

    async def promote_canary(self, deployment_id: str, *, actor_id: str, canary_percent: float = 100.0) -> DeploymentModel:
        """Widens (or narrows) an already-live canary's traffic share.
        Passing the default 100.0 completes the rollout to full traffic."""
        deployment = await self.repos.deployments.get_or_404(deployment_id)
        if deployment.status != DeploymentStatus.DEPLOYED.value:
            raise InvalidTransitionError(f"Cannot adjust canary traffic for a deployment in status '{deployment.status}'")
        if not (0.0 < canary_percent <= 100.0):
            raise ValidationError("canary_percent must be in (0, 100]")
        deployment.canary_percent = canary_percent
        return await self.repos.deployments.update(deployment)

    # -- rollback --------------------------------------------------------------

    async def rollback(
        self, prompt_id: str, environment: DeploymentEnvironment, *, actor_id: str,
        target_version_id: str | None = None, reason: str | None = None,
    ) -> DeploymentModel:
        """Rolls an environment back to a known-good version. With no
        `target_version_id`, rolls back to whatever was deployed
        immediately before the current live deployment. Rollback skips
        the approval workflow (it restores a state that was already
        approved and live), but is still recorded as its own deployment
        row linked via `rollback_of_id` for full audit history."""
        history = await self.repos.deployments.list_for_prompt(prompt_id, environment=environment.value)
        deployed_history = [d for d in history if d.status in (DeploymentStatus.DEPLOYED.value, DeploymentStatus.ROLLED_BACK.value)]
        if not deployed_history:
            raise DeploymentError(f"No deployment history for prompt '{prompt_id}' in environment '{environment.value}'")

        current = next((d for d in deployed_history if d.status == DeploymentStatus.DEPLOYED.value), None)
        if current is None:
            raise DeploymentError(f"No currently active deployment to roll back in environment '{environment.value}'")

        if target_version_id is None:
            prior = next((d for d in deployed_history if d.id != current.id), None)
            if prior is None:
                raise DeploymentError("No prior deployment exists to roll back to")
            target_version_id = prior.version_id

        current.status = DeploymentStatus.ROLLED_BACK.value
        await self.repos.deployments.update(current)

        rollback_deployment = DeploymentModel(
            prompt_id=prompt_id, version_id=target_version_id, environment=environment.value,
            status=DeploymentStatus.DEPLOYED.value, canary_percent=100.0, requested_by=actor_id,
            approved_by=actor_id, approved_at=utc_now(), deployed_at=utc_now(),
            rollback_of_id=current.id, notes=f"Rollback: {reason}" if reason else "Rollback",
        )
        return await self.repos.deployments.add(rollback_deployment)

    # -- queries -----------------------------------------------------------------

    async def get_current(self, prompt_id: str, environment: DeploymentEnvironment) -> DeploymentModel | None:
        return await self.repos.deployments.get_current_for_environment(prompt_id, environment.value)

    async def history(self, prompt_id: str, *, environment: DeploymentEnvironment | None = None) -> list[DeploymentModel]:
        return await self.repos.deployments.list_for_prompt(prompt_id, environment=environment.value if environment else None)

    # -- environment config (variables/secrets scoped per env) -------------------

    async def set_environment_config(self, workspace_id: str, environment: DeploymentEnvironment, variables: dict, *, updated_by: str) -> DeploymentEnvironmentConfigModel:
        existing = await self.repos.deployment_env_configs.get_for_workspace_env(workspace_id, environment.value)
        if existing:
            existing.variables = variables
            existing.updated_by = updated_by
            return await self.repos.deployment_env_configs.update(existing)
        return await self.repos.deployment_env_configs.add(
            DeploymentEnvironmentConfigModel(workspace_id=workspace_id, environment=environment.value, variables=variables, updated_by=updated_by)
        )

    async def get_environment_config(self, workspace_id: str, environment: DeploymentEnvironment) -> dict:
        config = await self.repos.deployment_env_configs.get_for_workspace_env(workspace_id, environment.value)
        return config.variables if config else {}
