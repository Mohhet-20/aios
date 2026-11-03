"""Import every model module so `Base.metadata` is fully populated
before `init_models()` (or Alembic) inspects it."""
from gateway_platform.models import (  # noqa: F401
    api_management,
    devx,
    events,
    gateway,
    integrations,
    mesh,
    observability,
    protocols,
    security,
    traffic,
    webhooks,
)
