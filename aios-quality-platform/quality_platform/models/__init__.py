"""Importing this package populates `Base.metadata` with every table
in the platform — required before `create_all()`/Alembic can see them."""
from __future__ import annotations

from quality_platform.models import (  # noqa: F401
    ai_quality,
    certification,
    chaos,
    failure_analysis,
    observability,
    performance,
    quality_gates,
    reliability,
    security_testing,
    testing,
    validation,
)
