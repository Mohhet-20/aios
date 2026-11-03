"""Import every model module so `Base.metadata` is fully populated
before `init_models()`/Alembic ever runs."""
from __future__ import annotations

from docs_platform.models import (  # noqa: F401
    analytics,
    api_sdk_docs,
    architecture,
    assistant,
    collaboration,
    documentation,
    knowledge_base,
    learning,
    search,
    security,
    versioning,
)
