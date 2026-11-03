"""Security policies (password/session/IP/geo/MFA/retention/approval),
security events, IP/geo restriction checks, risk scoring, and
administrative account recovery."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from identity_platform.dependencies.dependencies import (
    get_account_recovery_service,
    get_restriction_service,
    get_risk_scoring_service,
    get_security_event_service,
    get_security_policy_service,
)
from identity_platform.domain.enums import SecurityEventSeverity, SecurityEventType, SecurityPolicyType
from identity_platform.identity_api.serialization import to_dict, to_dict_list
from identity_platform.security_platform.account_recovery_service import AccountRecoveryService
from identity_platform.security_platform.restriction_service import RestrictionService
from identity_platform.security_platform.risk_service import RiskScoringService, RiskSignals
from identity_platform.security_platform.security_event_service import SecurityEventService
from identity_platform.security_platform.policy_service import SecurityPolicyService

router = APIRouter(prefix="/security", tags=["security"])


class SetPolicyRequest(BaseModel):
    organization_id: str | None
    policy_type: SecurityPolicyType
    config: dict
    is_active: bool = True


@router.put("/policies")
async def set_policy(body: SetPolicyRequest, service: SecurityPolicyService = Depends(get_security_policy_service)):
    return to_dict(await service.set_policy(body.organization_id, body.policy_type, config=body.config, is_active=body.is_active))


@router.get("/policies")
async def list_policies(organization_id: str | None = None, service: SecurityPolicyService = Depends(get_security_policy_service)):
    return to_dict_list(await service.list_for_organization(organization_id))


@router.post("/policies/{policy_id}/deactivate")
async def deactivate_policy(policy_id: str, service: SecurityPolicyService = Depends(get_security_policy_service)):
    return to_dict(await service.deactivate(policy_id))


class RecordEventRequest(BaseModel):
    event_type: SecurityEventType
    severity: SecurityEventSeverity
    organization_id: str | None = None
    user_id: str | None = None
    details: dict = {}


@router.post("/events", status_code=201)
async def record_security_event(body: RecordEventRequest, service: SecurityEventService = Depends(get_security_event_service)):
    return to_dict(await service.record_event(
        event_type=body.event_type, severity=body.severity, organization_id=body.organization_id,
        user_id=body.user_id, details=body.details,
    ))


@router.post("/events/{event_id}/resolve")
async def resolve_security_event(event_id: str, service: SecurityEventService = Depends(get_security_event_service)):
    return to_dict(await service.resolve_event(event_id))


@router.get("/events/unresolved")
async def list_unresolved_events(organization_id: str | None = None, service: SecurityEventService = Depends(get_security_event_service)):
    return to_dict_list(await service.list_unresolved(organization_id))


@router.get("/restrictions/ip")
async def check_ip_allowed(organization_id: str | None, ip_address: str, service: RestrictionService = Depends(get_restriction_service)):
    return {"allowed": await service.is_ip_allowed(organization_id, ip_address)}


@router.get("/restrictions/geo")
async def check_country_allowed(organization_id: str | None, country_code: str, service: RestrictionService = Depends(get_restriction_service)):
    return {"allowed": await service.is_country_allowed(organization_id, country_code)}


class ScoreRiskRequest(BaseModel):
    user_id: str
    organization_id: str | None = None
    is_new_device: bool = False
    is_new_country: bool = False
    recent_failed_attempts: int = 0
    impossible_travel: bool = False


@router.post("/risk/score")
async def score_risk(body: ScoreRiskRequest, service: RiskScoringService = Depends(get_risk_scoring_service)):
    signals = RiskSignals(
        is_new_device=body.is_new_device, is_new_country=body.is_new_country,
        recent_failed_attempts=body.recent_failed_attempts, impossible_travel=body.impossible_travel,
    )
    score = await service.score_and_record(user_id=body.user_id, organization_id=body.organization_id, signals=signals)
    return {"risk_score": score}


class AdminUnlockRequest(BaseModel):
    performed_by: str
    organization_id: str | None = None


@router.post("/recovery/users/{user_id}/unlock")
async def admin_unlock_account(user_id: str, body: AdminUnlockRequest, service: AccountRecoveryService = Depends(get_account_recovery_service)):
    return to_dict(await service.admin_unlock_account(user_id, performed_by=body.performed_by, organization_id=body.organization_id))


@router.post("/recovery/users/{user_id}/disable-mfa")
async def admin_disable_mfa(user_id: str, body: AdminUnlockRequest, service: AccountRecoveryService = Depends(get_account_recovery_service)):
    return {"factors_disabled": await service.admin_disable_mfa(user_id, performed_by=body.performed_by, organization_id=body.organization_id)}
