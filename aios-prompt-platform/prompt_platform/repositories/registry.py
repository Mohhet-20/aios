"""Wires every repository to one shared AsyncSession — used by UnitOfWork
so a service can touch multiple aggregates within a single transaction."""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from prompt_platform.repositories.collection_repository import (
    PromptCollectionItemRepository,
    PromptCollectionRepository,
)
from prompt_platform.repositories.deployment_repository import (
    DeploymentEnvironmentConfigRepository,
    DeploymentRepository,
)
from prompt_platform.repositories.evaluation_repository import (
    EvaluationResultRepository,
    EvaluationRunRepository,
)
from prompt_platform.repositories.experiment_repository import (
    ExperimentRepository,
    ExperimentResultRepository,
    ExperimentVariantRepository,
)
from prompt_platform.repositories.governance_repository import (
    AuditLogEntryRepository,
    PromptPermissionGrantRepository,
)
from prompt_platform.repositories.observability_repository import PromptExecutionLogRepository
from prompt_platform.repositories.optimization_repository import (
    OptimizationRunRepository,
    OptimizationSuggestionRepository,
)
from prompt_platform.repositories.prompt_repository import (
    PromptCategoryRepository,
    PromptFavoriteRepository,
    PromptRepository,
    PromptTagRepository,
)
from prompt_platform.repositories.testing_repository import (
    GoldenTestCaseRepository,
    TestResultRepository,
    TestRunRepository,
)
from prompt_platform.repositories.version_repository import (
    PromptDependencyRepository,
    PromptHistoryRepository,
    PromptReleaseRepository,
    PromptVersionRepository,
)
from prompt_platform.repositories.workspace_repository import (
    PromptProjectRepository,
    PromptWorkspaceRepository,
)


class RepositoryRegistry:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.workspaces = PromptWorkspaceRepository(session)
        self.projects = PromptProjectRepository(session)
        self.prompts = PromptRepository(session)
        self.categories = PromptCategoryRepository(session)
        self.tags = PromptTagRepository(session)
        self.favorites = PromptFavoriteRepository(session)
        self.collections = PromptCollectionRepository(session)
        self.collection_items = PromptCollectionItemRepository(session)
        self.versions = PromptVersionRepository(session)
        self.dependencies = PromptDependencyRepository(session)
        self.history = PromptHistoryRepository(session)
        self.releases = PromptReleaseRepository(session)
        self.golden_test_cases = GoldenTestCaseRepository(session)
        self.test_runs = TestRunRepository(session)
        self.test_results = TestResultRepository(session)
        self.evaluation_runs = EvaluationRunRepository(session)
        self.evaluation_results = EvaluationResultRepository(session)
        self.experiments = ExperimentRepository(session)
        self.experiment_variants = ExperimentVariantRepository(session)
        self.experiment_results = ExperimentResultRepository(session)
        self.deployments = DeploymentRepository(session)
        self.deployment_env_configs = DeploymentEnvironmentConfigRepository(session)
        self.execution_logs = PromptExecutionLogRepository(session)
        self.optimization_runs = OptimizationRunRepository(session)
        self.optimization_suggestions = OptimizationSuggestionRepository(session)
        self.audit_log = AuditLogEntryRepository(session)
        self.permission_grants = PromptPermissionGrantRepository(session)
