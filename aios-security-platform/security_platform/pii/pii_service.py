"""PII scanning (persisted findings, never storing raw values) and
sensitive data classification. DLP policy evaluation and secure
context assembly live in `dlp/dlp_service.py`, which builds on the
detectors here."""
from __future__ import annotations

from security_platform.config.settings import Settings, get_settings
from security_platform.models.data_protection import DataClassificationModel, PiiFindingModel
from security_platform.pii.detectors import detect_pii, hash_value, mask_value, redact_pii
from security_platform.repositories.registry import RepositoryRegistry


class PiiService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def scan_pii(self, tenant_id: str, source_type: str, source_id: str | None, text: str) -> list[PiiFindingModel]:
        findings = []
        for match in detect_pii(text):
            finding = PiiFindingModel(
                tenant_id=tenant_id, source_type=source_type, source_id=source_id, entity_type=match.entity_type.value,
                value_hash=hash_value(match.value), redacted_preview=mask_value(match.value, match.entity_type), confidence=0.8,
            )
            findings.append(await self.repos.pii_findings.add(finding))
        return findings

    def mask_text(self, text: str) -> str:
        """Automatic Data Masking: convenience wrapper with no
        persistence, for callers that just need PII stripped from
        text before it's logged, displayed, or sent onward."""
        return redact_pii(text)

    async def classify_resource(
        self, tenant_id: str, resource_type: str, resource_id: str, sensitivity: str, *,
        classified_by: str | None = None, rationale: str | None = None,
    ) -> DataClassificationModel:
        existing = await self.repos.data_classifications.get_for_resource(tenant_id, resource_type, resource_id)
        if existing is not None:
            existing.sensitivity = sensitivity
            existing.classified_by = classified_by
            existing.rationale = rationale
            return await self.repos.data_classifications.update(existing)
        created = DataClassificationModel(
            tenant_id=tenant_id, resource_type=resource_type, resource_id=resource_id, sensitivity=sensitivity,
            classified_by=classified_by, rationale=rationale,
        )
        return await self.repos.data_classifications.add(created)
