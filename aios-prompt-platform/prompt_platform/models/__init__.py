"""Import every model module so `Base.metadata` is fully populated before
`init_models()`/Alembic ever runs."""
from prompt_platform.models.collection import PromptCollectionItemModel, PromptCollectionModel
from prompt_platform.models.deployment import DeploymentEnvironmentConfigModel, DeploymentModel
from prompt_platform.models.evaluation import EvaluationResultModel, EvaluationRunModel
from prompt_platform.models.experiment import ExperimentModel, ExperimentResultModel, ExperimentVariantModel
from prompt_platform.models.governance import AuditLogEntryModel, PromptPermissionGrantModel
from prompt_platform.models.observability import PromptExecutionLogModel
from prompt_platform.models.optimization import OptimizationRunModel, OptimizationSuggestionModel
from prompt_platform.models.prompt import (
    PromptCategoryModel,
    PromptFavoriteModel,
    PromptModel,
    PromptTagLinkModel,
    PromptTagModel,
)
from prompt_platform.models.testing import GoldenTestCaseModel, TestResultModel, TestRunModel
from prompt_platform.models.version import (
    PromptDependencyModel,
    PromptHistoryModel,
    PromptReleaseModel,
    PromptVersionModel,
)
from prompt_platform.models.workspace import PromptProjectModel, PromptWorkspaceModel

__all__ = [
    "AuditLogEntryModel",
    "DeploymentEnvironmentConfigModel",
    "DeploymentModel",
    "EvaluationResultModel",
    "EvaluationRunModel",
    "ExperimentModel",
    "ExperimentResultModel",
    "ExperimentVariantModel",
    "GoldenTestCaseModel",
    "OptimizationRunModel",
    "OptimizationSuggestionModel",
    "PromptCategoryModel",
    "PromptCollectionItemModel",
    "PromptCollectionModel",
    "PromptDependencyModel",
    "PromptExecutionLogModel",
    "PromptFavoriteModel",
    "PromptHistoryModel",
    "PromptModel",
    "PromptPermissionGrantModel",
    "PromptProjectModel",
    "PromptReleaseModel",
    "PromptTagLinkModel",
    "PromptTagModel",
    "PromptVersionModel",
    "PromptWorkspaceModel",
    "TestResultModel",
    "TestRunModel",
]
