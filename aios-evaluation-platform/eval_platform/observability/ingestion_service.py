"""ObservabilityIngestionService: validates and persists one
`ObservabilityEventModel` per call. Every upstream AIOS platform
(prompt/agent/workflow/tool/memory) reports its own execution events
through this single entry point — `source_platform` distinguishes
origin, `source_execution_id` correlates an event back to the
originating platform's own execution record. Genuinely-measured fields
only: `resource_usage`/`token_usage`/`cost` are left empty rather than
estimated when the caller has no real measurement to report."""
from __future__ import annotations

from eval_platform.core.exceptions import ValidationError
from eval_platform.domain.enums import ObservabilityEventStatus, ObservabilityEventType
from eval_platform.models.observability import ObservabilityEventModel
from eval_platform.repositories.registry import RepositoryRegistry

_VALID_EVENT_TYPES = {t.value for t in ObservabilityEventType}
_VALID_STATUSES = {s.value for s in ObservabilityEventStatus}


class ObservabilityIngestionService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def ingest_event(
        self, workspace_id: str, *, event_type: str, source_platform: str, status: str,
        source_execution_id: str | None = None, latency_ms: float | None = None, queue_time_ms: float | None = None,
        error_type: str | None = None, retry_count: int = 0, token_usage: dict | None = None,
        cost: float | None = None, resource_usage: dict | None = None, payload: dict | None = None,
        error_message: str | None = None,
    ) -> ObservabilityEventModel:
        if event_type not in _VALID_EVENT_TYPES:
            raise ValidationError(f"unknown event_type '{event_type}' (must be one of {sorted(_VALID_EVENT_TYPES)})")
        if status not in _VALID_STATUSES:
            raise ValidationError(f"unknown status '{status}' (must be one of {sorted(_VALID_STATUSES)})")
        if status == ObservabilityEventStatus.FAILED.value and not error_type and not error_message:
            raise ValidationError("a failed event must report an error_type or error_message")
        if retry_count < 0:
            raise ValidationError("retry_count cannot be negative")

        return await self.repos.observability_events.add(ObservabilityEventModel(
            workspace_id=workspace_id, event_type=event_type, source_platform=source_platform, status=status,
            source_execution_id=source_execution_id, latency_ms=latency_ms, queue_time_ms=queue_time_ms,
            error_type=error_type, retry_count=retry_count, token_usage=token_usage or {}, cost=cost,
            resource_usage=resource_usage or {}, payload=payload or {}, error_message=error_message,
        ))
