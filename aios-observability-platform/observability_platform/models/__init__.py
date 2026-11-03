"""Import every ORM model so `Base.metadata` is fully populated before
`init_models()`/Alembic autogenerate runs."""
from observability_platform.models.alerts import (  # noqa: F401
    AlertEscalationModel,
    AlertModel,
    AlertNotificationModel,
    AlertRuleModel,
    EscalationPolicyModel,
    MaintenanceWindowModel,
    NotificationChannelModel,
)
from observability_platform.models.capacity import CapacityForecastModel, CapacitySnapshotModel  # noqa: F401
from observability_platform.models.components import ComponentModel  # noqa: F401
from observability_platform.models.dashboards import DashboardModel  # noqa: F401
from observability_platform.models.governance import (  # noqa: F401
    AccessGrantModel,
    AuditLogEntryModel,
    RetentionPolicyModel,
)
from observability_platform.models.health import HealthCheckResultModel  # noqa: F401
from observability_platform.models.incidents import (  # noqa: F401
    IncidentModel,
    IncidentPostmortemModel,
    IncidentTimelineEventModel,
)
from observability_platform.models.logs import LogEntryModel  # noqa: F401
from observability_platform.models.metrics import MetricDefinitionModel, MetricPointModel  # noqa: F401
from observability_platform.models.reporting import ReportModel  # noqa: F401
from observability_platform.models.topology import TopologyEdgeModel, TopologyNodeModel  # noqa: F401
from observability_platform.models.tracing import SpanModel, TraceModel  # noqa: F401
