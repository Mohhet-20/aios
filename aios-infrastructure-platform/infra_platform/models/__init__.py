"""Import every model module so `Base.metadata` is fully populated
before `init_models()`/Alembic runs — identical pattern to every
prior AIOS platform."""
from __future__ import annotations

from infra_platform.models import (  # noqa: F401
    artifacts,
    autoscaling,
    cicd,
    cloud,
    containers,
    deployment,
    experiments,
    feature_store,
    inference,
    kubernetes,
    model_registry,
    observability,
    recovery,
    security,
    services,
)
