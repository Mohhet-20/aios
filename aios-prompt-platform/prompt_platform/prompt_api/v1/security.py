"""Prompt Security: on-demand scanning utilities for injection risk and
secret exposure — used by clients (e.g. Studio) that want to check text
before it's saved or sent, independent of the hard-fail check
VersioningService.create_version already applies automatically."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from prompt_platform.prompt_api.dependencies import get_security_service
from prompt_platform.prompt_security.security_service import SecurityService

router = APIRouter(prefix="/security", tags=["security"])


class ScanRequest(BaseModel):
    text: str


class SanitizeRequest(BaseModel):
    variables: dict


@router.post("/scan")
async def scan(body: ScanRequest, svc: SecurityService = Depends(get_security_service)):
    report = svc.validate_output(body.text)
    return {"injection_matches": report.injection_matches, "secret_matches": report.secret_matches, "is_safe": report.is_safe}


@router.post("/sanitize-variables")
async def sanitize_variables(body: SanitizeRequest, svc: SecurityService = Depends(get_security_service)):
    return svc.sanitize_variables(body.variables)


@router.post("/redact")
async def redact(body: ScanRequest, svc: SecurityService = Depends(get_security_service)):
    return {"redacted": svc.redact_for_storage(body.text)}
