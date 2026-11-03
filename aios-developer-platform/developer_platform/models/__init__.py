"""Import every model module so `Base.metadata` is fully populated
before `init_models()` (or Alembic) inspects it."""
from developer_platform.models import (  # noqa: F401
    analytics,
    api_platform,
    cli,
    codegen,
    extensions,
    mcp,
    plugins,
    portal,
    registry,
    sdk,
    security,
    webhooks,
)
