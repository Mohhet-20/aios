"""Import every model module so `Base.metadata` is fully populated
before `init_models()` runs (test/dev schema creation) or Alembic
autogenerate inspects it."""
from __future__ import annotations

from analytics_platform.models import (  # noqa: F401
    analytics,
    dashboards,
    exports,
    forecasts,
    kpis,
    observability,
    recommendations,
    reports,
    security,
    warehouse,
)
