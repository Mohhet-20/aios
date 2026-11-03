"""Base domain event type. Pure dataclass, no infrastructure imports — the
domain layer only *declares* that these events exist; `app.events.bus`
(infrastructure) is what actually dispatches them to subscribers. This keeps
the domain layer importable with zero framework dependencies, per Clean
Architecture's dependency-inversion rule.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime

from app.clock import utc_now


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=lambda: utc_now())
    organization_id: str | None = None
    actor_id: str | None = None

    @property
    def event_name(self) -> str:
        return self.__class__.__name__
