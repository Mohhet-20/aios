"""Log ingestion. Every entry is masked for sensitive fields in its
`context`/`tags` payloads before it's ever persisted — masking happens
here, at the single choke point every ingestion path routes through,
not as an afterthought at read time (by then the sensitive value would
already be sitting in the database)."""
from __future__ import annotations

from observability_platform.core.exceptions import LogPayloadTooLargeError, ValidationError
from observability_platform.config.settings import Settings, get_settings
from observability_platform.domain.enums import LogLevel
from observability_platform.models.logs import LogEntryModel
from observability_platform.repositories.registry import RepositoryRegistry
from observability_platform.security.masking import mask_sensitive


class LogIngestService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def ingest(
        self,
        tenant_id: str,
        *,
        service_name: str,
        level: str,
        message: str,
        component_type: str | None = None,
        context: dict | None = None,
        tags: dict | None = None,
        correlation_id: str | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
        session_id: str | None = None,
        user_id: str | None = None,
        request_id: str | None = None,
    ) -> LogEntryModel:
        if level not in {lvl.value for lvl in LogLevel}:
            raise ValidationError(f"Unknown log level '{level}'")
        if len(message.encode("utf-8")) > self.settings.log_max_message_bytes:
            raise LogPayloadTooLargeError(
                f"Log message exceeds max size of {self.settings.log_max_message_bytes} bytes"
            )
        entry = LogEntryModel(
            tenant_id=tenant_id,
            service_name=service_name,
            component_type=component_type,
            level=level,
            message=message,
            context=mask_sensitive(context or {}),
            tags=mask_sensitive(tags or {}),
            correlation_id=correlation_id,
            trace_id=trace_id,
            span_id=span_id,
            session_id=session_id,
            user_id=user_id,
            request_id=request_id,
        )
        return await self.repos.log_entries.add(entry)

    async def ingest_batch(self, tenant_id: str, entries: list[dict]) -> list[LogEntryModel]:
        """Ingests up to `log_rotation_max_events_per_batch` entries in
        one call. Each entry dict uses the same keyword shape as
        `ingest`'s parameters (minus `tenant_id`)."""
        if len(entries) > self.settings.log_rotation_max_events_per_batch:
            raise LogPayloadTooLargeError(
                f"Batch of {len(entries)} exceeds max batch size of "
                f"{self.settings.log_rotation_max_events_per_batch}"
            )
        results = []
        for entry in entries:
            results.append(await self.ingest(tenant_id, **entry))
        return results
