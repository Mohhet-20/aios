"""Import every ORM model so `Base.metadata` is fully populated before
`create_all()` runs — the same explicit-import pattern every prior AIOS
platform's models package uses."""
from eval_platform.models.alert import AlertModel, AlertRuleModel
from eval_platform.models.analytics import AnalyticsSnapshotModel, RecommendationModel
from eval_platform.models.benchmark import BenchmarkCandidateResultModel, BenchmarkModel, BenchmarkRunModel
from eval_platform.models.dataset import DatasetItemModel, DatasetModel, DatasetVersionModel
from eval_platform.models.evaluation import EvaluationModel, EvaluationVersionModel
from eval_platform.models.governance import AuditLogEntryModel, PermissionGrantModel
from eval_platform.models.hallucination import HallucinationCheckModel
from eval_platform.models.metric import MetricDefinitionModel, MetricResultModel
from eval_platform.models.observability import ObservabilityEventModel
from eval_platform.models.run import EvaluationItemResultModel, EvaluationRunModel
from eval_platform.models.workspace import WorkspaceModel

__all__ = [
    "WorkspaceModel",
    "EvaluationModel",
    "EvaluationVersionModel",
    "EvaluationRunModel",
    "EvaluationItemResultModel",
    "DatasetModel",
    "DatasetVersionModel",
    "DatasetItemModel",
    "BenchmarkModel",
    "BenchmarkRunModel",
    "BenchmarkCandidateResultModel",
    "MetricDefinitionModel",
    "MetricResultModel",
    "HallucinationCheckModel",
    "ObservabilityEventModel",
    "AlertRuleModel",
    "AlertModel",
    "AnalyticsSnapshotModel",
    "RecommendationModel",
    "PermissionGrantModel",
    "AuditLogEntryModel",
]
