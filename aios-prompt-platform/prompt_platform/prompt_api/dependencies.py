"""FastAPI dependency wiring: DB session -> RepositoryRegistry -> every
service, plus AI Core and a minimal caller-identity dependency.

Auth is intentionally minimal here: this platform expects to sit behind
an already-authenticated gateway (e.g. the AIOS backend from Phase 3,
which owns full JWT/session auth) that forwards the caller's identity via
the `X-User-Id` header. Swapping this dependency for real token
validation is a drop-in change — every router already depends on
`get_current_actor_id`, never on the header directly.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from ai_core.bootstrap import AICoreContext
from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from prompt_platform.database.session import get_db_session
from prompt_platform.dependencies.ai_core_provider import get_default_ai_core_context
from prompt_platform.prompt_deployment.deployment_service import DeploymentService
from prompt_platform.prompt_editor.autosave import AutosaveService
from prompt_platform.prompt_editor.execution import StudioExecutionService
from prompt_platform.prompt_editor.preview import PreviewService
from prompt_platform.prompt_engine.prompt_service import PromptService
from prompt_platform.prompt_engine.versioning_service import VersioningService
from prompt_platform.prompt_evaluation.evaluation_service import EvaluationService
from prompt_platform.prompt_experiments.experiment_service import ExperimentService
from prompt_platform.prompt_governance.governance_service import GovernanceService
from prompt_platform.prompt_observability.observability_service import ObservabilityService
from prompt_platform.prompt_optimization.optimization_service import OptimizationService
from prompt_platform.prompt_registry.library_service import PromptLibraryService
from prompt_platform.prompt_security.security_service import SecurityService
from prompt_platform.prompt_testing.test_service import PromptTestingService
from prompt_platform.repositories.registry import RepositoryRegistry


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


async def get_repos(session: AsyncSession = Depends(get_session, scope="function")) -> RepositoryRegistry:
    return RepositoryRegistry(session)


def get_ai_core() -> AICoreContext:
    return get_default_ai_core_context()


async def get_current_actor_id(x_user_id: str | None = Header(default=None)) -> str:
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id


# -- per-service factories ----------------------------------------------------------

def get_prompt_service(repos: RepositoryRegistry = Depends(get_repos)) -> PromptService:
    return PromptService(repos)


def get_versioning_service(repos: RepositoryRegistry = Depends(get_repos)) -> VersioningService:
    return VersioningService(repos)


def get_library_service(repos: RepositoryRegistry = Depends(get_repos)) -> PromptLibraryService:
    return PromptLibraryService(repos)


def get_preview_service(ai_core: AICoreContext = Depends(get_ai_core)) -> PreviewService:
    return PreviewService(ai_core)


def get_studio_execution_service(ai_core: AICoreContext = Depends(get_ai_core)) -> StudioExecutionService:
    return StudioExecutionService(ai_core)


def get_autosave_service(repos: RepositoryRegistry = Depends(get_repos)) -> AutosaveService:
    return AutosaveService(repos)


def get_testing_service(
    repos: RepositoryRegistry = Depends(get_repos), ai_core: AICoreContext = Depends(get_ai_core)
) -> PromptTestingService:
    return PromptTestingService(repos, ai_core)


def get_evaluation_service(
    repos: RepositoryRegistry = Depends(get_repos), ai_core: AICoreContext = Depends(get_ai_core)
) -> EvaluationService:
    return EvaluationService(repos, ai_core)


def get_optimization_service(
    repos: RepositoryRegistry = Depends(get_repos), ai_core: AICoreContext = Depends(get_ai_core)
) -> OptimizationService:
    return OptimizationService(repos, ai_core)


def get_experiment_service(
    repos: RepositoryRegistry = Depends(get_repos), ai_core: AICoreContext = Depends(get_ai_core)
) -> ExperimentService:
    return ExperimentService(repos, ai_core)


def get_deployment_service(repos: RepositoryRegistry = Depends(get_repos)) -> DeploymentService:
    return DeploymentService(repos)


def get_observability_service(repos: RepositoryRegistry = Depends(get_repos)) -> ObservabilityService:
    return ObservabilityService(repos)


def get_governance_service(repos: RepositoryRegistry = Depends(get_repos)) -> GovernanceService:
    return GovernanceService(repos)


def get_security_service() -> SecurityService:
    return SecurityService()
