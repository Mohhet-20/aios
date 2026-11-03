"""Orchestrates the threat detectors: runs the relevant check, and
when it fires, persists a `ThreatDetectionModel` (append-per-incident,
not append-per-evaluation — see the model's docstring) and exposes the
detected -> investigating -> confirmed/dismissed -> mitigated lifecycle
over it via the guarded `ThreatDetection` domain entity."""
from __future__ import annotations

from datetime import datetime

from security_platform.config.settings import Settings, get_settings
from security_platform.domain.entities import ThreatDetection as ThreatEntity
from security_platform.domain.enums import ThreatSeverity, ThreatStatus, ThreatType
from security_platform.guardrails.detectors import detect_jailbreak, detect_prompt_injection
from security_platform.models.threats import ThreatDetectionModel
from security_platform.repositories.registry import RepositoryRegistry
from security_platform.threat_detection.detectors import (
    detect_anomaly,
    detect_api_abuse,
    detect_behavior_deviation,
    detect_brute_force,
    detect_credential_abuse,
    detect_privilege_escalation,
    detect_suspicious_workflow,
    detect_tool_abuse,
)


def _to_entity(model: ThreatDetectionModel) -> ThreatEntity:
    return ThreatEntity(id=model.id, status=ThreatStatus(model.status), resolved_at=model.resolved_at)


class ThreatDetectionService:
    def __init__(self, repos: RepositoryRegistry, *, settings: Settings | None = None):
        self.repos = repos
        self.settings = settings or get_settings()

    async def _record(
        self, tenant_id: str, threat_type: str, severity: str, *, entity_type: str | None, entity_id: str | None,
        description: str, evidence: dict,
    ) -> ThreatDetectionModel:
        return await self.repos.threat_detections.add(
            ThreatDetectionModel(
                tenant_id=tenant_id, threat_type=threat_type, severity=severity, status=ThreatStatus.DETECTED.value,
                entity_type=entity_type, entity_id=entity_id, description=description, evidence=evidence,
            )
        )

    async def check_brute_force(
        self, tenant_id: str, entity_type: str, entity_id: str, attempt_timestamps: list[datetime]
    ) -> ThreatDetectionModel | None:
        if not detect_brute_force(attempt_timestamps, threshold=self.settings.brute_force_attempt_threshold, window_seconds=self.settings.brute_force_window_seconds):
            return None
        return await self._record(
            tenant_id, ThreatType.BRUTE_FORCE.value, ThreatSeverity.HIGH.value, entity_type=entity_type, entity_id=entity_id,
            description=f"{len(attempt_timestamps)} attempts observed within the brute-force detection window",
            evidence={"attempt_count": len(attempt_timestamps), "window_seconds": self.settings.brute_force_window_seconds},
        )

    async def check_api_abuse(
        self, tenant_id: str, entity_type: str, entity_id: str, request_timestamps: list[datetime]
    ) -> ThreatDetectionModel | None:
        if not detect_api_abuse(request_timestamps, threshold=self.settings.api_abuse_rate_threshold, window_seconds=self.settings.api_abuse_window_seconds):
            return None
        return await self._record(
            tenant_id, ThreatType.API_ABUSE.value, ThreatSeverity.MEDIUM.value, entity_type=entity_type, entity_id=entity_id,
            description=f"{len(request_timestamps)} requests observed within the API-abuse detection window",
            evidence={"request_count": len(request_timestamps), "window_seconds": self.settings.api_abuse_window_seconds},
        )

    async def check_tool_abuse(
        self, tenant_id: str, entity_type: str, entity_id: str, call_timestamps: list[datetime], *, threshold: int = 100, window_seconds: int = 60
    ) -> ThreatDetectionModel | None:
        if not detect_tool_abuse(call_timestamps, threshold=threshold, window_seconds=window_seconds):
            return None
        return await self._record(
            tenant_id, ThreatType.TOOL_ABUSE.value, ThreatSeverity.MEDIUM.value, entity_type=entity_type, entity_id=entity_id,
            description=f"{len(call_timestamps)} tool calls observed within the tool-abuse detection window",
            evidence={"call_count": len(call_timestamps), "window_seconds": window_seconds},
        )

    async def check_privilege_escalation(
        self, tenant_id: str, entity_type: str, entity_id: str, *, previous_role_rank: int, new_role_rank: int, approved: bool
    ) -> ThreatDetectionModel | None:
        if not detect_privilege_escalation(previous_role_rank, new_role_rank, approved=approved):
            return None
        return await self._record(
            tenant_id, ThreatType.PRIVILEGE_ESCALATION.value, ThreatSeverity.CRITICAL.value, entity_type=entity_type, entity_id=entity_id,
            description="Unapproved privilege escalation detected",
            evidence={"previous_role_rank": previous_role_rank, "new_role_rank": new_role_rank},
        )

    async def check_credential_abuse(
        self, tenant_id: str, entity_type: str, entity_id: str, *, distinct_source_count: int, threshold: int = 3
    ) -> ThreatDetectionModel | None:
        if not detect_credential_abuse(distinct_source_count, threshold=threshold):
            return None
        return await self._record(
            tenant_id, ThreatType.CREDENTIAL_ABUSE.value, ThreatSeverity.HIGH.value, entity_type=entity_type, entity_id=entity_id,
            description=f"Same credential used from {distinct_source_count} distinct sources",
            evidence={"distinct_source_count": distinct_source_count},
        )

    async def check_suspicious_workflow(
        self, tenant_id: str, entity_type: str, entity_id: str, *, step_count: int, external_call_count: int
    ) -> ThreatDetectionModel | None:
        if not detect_suspicious_workflow(step_count, external_call_count):
            return None
        return await self._record(
            tenant_id, ThreatType.SUSPICIOUS_WORKFLOW.value, ThreatSeverity.MEDIUM.value, entity_type=entity_type, entity_id=entity_id,
            description="Workflow exceeds normal step/external-call bounds",
            evidence={"step_count": step_count, "external_call_count": external_call_count},
        )

    async def check_malicious_prompt(
        self, tenant_id: str, entity_type: str, entity_id: str, text: str
    ) -> ThreatDetectionModel | None:
        injection = detect_prompt_injection(text)
        jailbreak = detect_jailbreak(text)
        risk_score = max(injection.risk_score, jailbreak.risk_score)
        signals = injection.signals + jailbreak.signals
        if risk_score < 0.6 or not signals:
            return None
        return await self._record(
            tenant_id, ThreatType.MALICIOUS_PROMPT.value, ThreatSeverity.HIGH.value, entity_type=entity_type, entity_id=entity_id,
            description=f"High-risk prompt detected (score={risk_score:.2f})", evidence={"risk_score": risk_score, "signals": signals},
        )

    async def check_anomaly(
        self, tenant_id: str, entity_type: str, entity_id: str, metric_name: str, value: float, baseline: list[float], *, z_threshold: float = 3.0
    ) -> ThreatDetectionModel | None:
        result = detect_anomaly(value, baseline, z_threshold=z_threshold)
        if not result.is_anomaly:
            return None
        return await self._record(
            tenant_id, ThreatType.ANOMALY.value, ThreatSeverity.MEDIUM.value, entity_type=entity_type, entity_id=entity_id,
            description=f"Anomalous value for '{metric_name}' (z-score={result.z_score:.2f})",
            evidence={"metric_name": metric_name, "value": value, "z_score": result.z_score},
        )

    async def check_behavior(
        self, tenant_id: str, entity_type: str, entity_id: str, recent_actions: list[str], typical_actions: set[str]
    ) -> ThreatDetectionModel | None:
        result = detect_behavior_deviation(recent_actions, typical_actions)
        if not result.is_deviant:
            return None
        return await self._record(
            tenant_id, ThreatType.BEHAVIOR.value, ThreatSeverity.LOW.value, entity_type=entity_type, entity_id=entity_id,
            description=f"Novel actions outside established behavior baseline: {result.novel_actions}",
            evidence={"novel_actions": result.novel_actions},
        )

    async def investigate(self, tenant_id: str, threat_id: str) -> ThreatDetectionModel:
        threat = await self.repos.threat_detections.get_or_404(threat_id)
        entity = _to_entity(threat)
        entity.investigate()
        threat.status = entity.status.value
        return await self.repos.threat_detections.update(threat)

    async def confirm(self, tenant_id: str, threat_id: str) -> ThreatDetectionModel:
        threat = await self.repos.threat_detections.get_or_404(threat_id)
        entity = _to_entity(threat)
        entity.confirm()
        threat.status = entity.status.value
        return await self.repos.threat_detections.update(threat)

    async def dismiss(self, tenant_id: str, threat_id: str, *, resolution_notes: str | None = None) -> ThreatDetectionModel:
        threat = await self.repos.threat_detections.get_or_404(threat_id)
        entity = _to_entity(threat)
        entity.dismiss()
        threat.status = entity.status.value
        threat.resolved_at = entity.resolved_at
        if resolution_notes is not None:
            threat.resolution_notes = resolution_notes
        return await self.repos.threat_detections.update(threat)

    async def mitigate(self, tenant_id: str, threat_id: str, *, resolution_notes: str | None = None) -> ThreatDetectionModel:
        threat = await self.repos.threat_detections.get_or_404(threat_id)
        entity = _to_entity(threat)
        entity.mitigate()
        threat.status = entity.status.value
        threat.resolved_at = entity.resolved_at
        if resolution_notes is not None:
            threat.resolution_notes = resolution_notes
        return await self.repos.threat_detections.update(threat)
