"""DLP policy evaluation (allow/flag/redact/block) and secure context
assembly — the security-filtering counterpart to the Memory Platform's
context assembly engine, dropping/redacting fragments before they're
handed to an LLM context window.

Retention and deletion *policy definitions* live in the Compliance
module (`RetentionPolicyModel`) since they're shared across every
regulated-data concern, not just PII — this service is where
detection and in-the-moment enforcement (mask/flag/block) happens."""
from __future__ import annotations

from security_platform.config.settings import Settings, get_settings
from security_platform.core.exceptions import DlpBlockError
from security_platform.domain.enums import DataSensitivity, DlpAction
from security_platform.models.data_protection import DlpIncidentModel
from security_platform.pii.detectors import ENTITY_SENSITIVITY, detect_pii, redact_pii
from security_platform.repositories.registry import RepositoryRegistry

_ACTION_RANK = {DlpAction.ALLOW.value: 0, DlpAction.FLAG.value: 1, DlpAction.REDACT.value: 2, DlpAction.BLOCK.value: 3}
_SEVERITY_FOR_SENSITIVITY_RANK = {0: "low", 1: "low", 2: "medium", 3: "critical"}


class DlpService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def evaluate_dlp(
        self, tenant_id: str, text: str, *, resource_type: str | None = None, resource_id: str | None = None,
    ) -> tuple[list[DlpIncidentModel], str, str]:
        """Returns (incidents, action_taken, output_text). Raises
        DlpBlockError (after persisting the incident record) when the
        resolved action is BLOCK."""
        matches = detect_pii(text)
        if not matches:
            return [], DlpAction.ALLOW.value, text

        worst_match = max(matches, key=lambda m: DataSensitivity(ENTITY_SENSITIVITY[m.entity_type]).rank)
        detected_sensitivity = ENTITY_SENSITIVITY[worst_match.entity_type]
        detected_rank = DataSensitivity(detected_sensitivity).rank

        policies = await self.repos.dlp_policies.list_enabled(tenant_id)
        triggered = [p for p in policies if DataSensitivity(p.sensitivity_threshold).rank <= detected_rank]
        if not triggered:
            return [], DlpAction.ALLOW.value, text

        action = max((p.action for p in triggered), key=lambda a: _ACTION_RANK.get(a, 0))
        severity = _SEVERITY_FOR_SENSITIVITY_RANK[detected_rank]
        if severity == "critical" and self.settings.dlp_block_on_critical and _ACTION_RANK[DlpAction.BLOCK.value] > _ACTION_RANK.get(action, 0):
            action = DlpAction.BLOCK.value

        entity_types = sorted({m.entity_type.value for m in matches})
        incidents = [
            await self.repos.dlp_incidents.add(
                DlpIncidentModel(
                    tenant_id=tenant_id, policy_id=policy.id, resource_type=resource_type, resource_id=resource_id,
                    severity=severity, action_taken=action, details={"entity_types": entity_types},
                )
            )
            for policy in triggered
        ]

        output_text = redact_pii(text, matches) if action == DlpAction.REDACT.value else text
        if action == DlpAction.BLOCK.value:
            raise DlpBlockError(f"DLP policy blocked content (sensitivity={detected_sensitivity}, entities={entity_types})")
        return incidents, action, output_text

    async def assemble_secure_context(
        self, tenant_id: str, fragments: list[dict], *, max_sensitivity: str = DataSensitivity.CONFIDENTIAL.value,
    ) -> list[str]:
        """Given fragments of `{"text": str, "resource_type": str | None, "resource_id": str | None}`
        destined for an LLM context window: drop any fragment whose
        resource classification exceeds `max_sensitivity`, then
        PII-redact whatever survives."""
        max_rank = DataSensitivity(max_sensitivity).rank
        safe_fragments: list[str] = []
        for fragment in fragments:
            resource_type = fragment.get("resource_type")
            resource_id = fragment.get("resource_id")
            if resource_type and resource_id:
                classification = await self.repos.data_classifications.get_for_resource(tenant_id, resource_type, resource_id)
                if classification is not None and DataSensitivity(classification.sensitivity).rank > max_rank:
                    continue
            safe_fragments.append(redact_pii(fragment["text"]))
        return safe_fragments
