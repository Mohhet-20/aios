"""Security & Supply Chain: SBOM records, artifact signing/
verification, and the release-approval workflow."""
from __future__ import annotations

import base64

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from release_platform.dependencies.dependencies import (
    get_artifact_signature_service,
    get_current_tenant_id,
    get_release_approval_service,
    get_sbom_service,
)
from release_platform.release_api.serialization import to_dict, to_dict_list
from release_platform.security.release_approval_service import ReleaseApprovalService
from release_platform.security.sbom_service import SbomService
from release_platform.security.signature_service import ArtifactSignatureService

router = APIRouter(prefix="/sboms", tags=["security"])
signatures_router = APIRouter(prefix="/artifact-signatures", tags=["security"])
approvals_router = APIRouter(prefix="/release-approvals", tags=["security"])


class GenerateSbomRequest(BaseModel):
    artifact_id: str
    format: str = "cyclonedx"
    content_ref: str = ""


@router.post("", status_code=201)
async def generate_sbom(
    body: GenerateSbomRequest, tenant_id: str = Depends(get_current_tenant_id), service: SbomService = Depends(get_sbom_service),
):
    return to_dict(await service.generate_sbom(tenant_id, **body.model_dump()))


@router.get("/by-artifact/{artifact_id}")
async def list_sboms_for_artifact(
    artifact_id: str, tenant_id: str = Depends(get_current_tenant_id), service: SbomService = Depends(get_sbom_service),
):
    return to_dict_list(await service.list_for_artifact(tenant_id, artifact_id))


class SignArtifactRequest(BaseModel):
    artifact_id: str
    payload_b64: str
    secret: str
    algorithm: str = "sha256"
    signed_by: str | None = None


@signatures_router.post("", status_code=201)
async def sign_artifact(
    body: SignArtifactRequest, tenant_id: str = Depends(get_current_tenant_id), service: ArtifactSignatureService = Depends(get_artifact_signature_service),
):
    payload = base64.b64decode(body.payload_b64)
    signature = await service.sign_artifact(
        tenant_id, artifact_id=body.artifact_id, payload=payload, secret=body.secret, algorithm=body.algorithm, signed_by=body.signed_by,
    )
    return to_dict(signature)


class VerifyArtifactSignatureRequest(BaseModel):
    artifact_id: str
    payload_b64: str
    secret: str


@signatures_router.post("/verify")
async def verify_artifact_signature(
    body: VerifyArtifactSignatureRequest, tenant_id: str = Depends(get_current_tenant_id), service: ArtifactSignatureService = Depends(get_artifact_signature_service),
):
    payload = base64.b64decode(body.payload_b64)
    signature = await service.verify_artifact_signature(tenant_id, artifact_id=body.artifact_id, payload=payload, secret=body.secret)
    return {"verified": True, "signature_id": signature.id}


@signatures_router.get("/by-artifact/{artifact_id}")
async def list_signatures_for_artifact(
    artifact_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ArtifactSignatureService = Depends(get_artifact_signature_service),
):
    return to_dict_list(await service.list_for_artifact(tenant_id, artifact_id))


class RequestApprovalRequest(BaseModel):
    release_id: str
    approver_id: str


@approvals_router.post("", status_code=201)
async def request_approval(
    body: RequestApprovalRequest, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseApprovalService = Depends(get_release_approval_service),
):
    return to_dict(await service.request_approval(tenant_id, **body.model_dump()))


class DecideApprovalRequest(BaseModel):
    decision: str
    notes: str = ""


@approvals_router.post("/{approval_id}/decide")
async def decide_approval(
    approval_id: str, body: DecideApprovalRequest,
    tenant_id: str = Depends(get_current_tenant_id), service: ReleaseApprovalService = Depends(get_release_approval_service),
):
    return to_dict(await service.decide(tenant_id, approval_id, **body.model_dump()))


@approvals_router.get("/by-release/{release_id}")
async def list_approvals_for_release(
    release_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseApprovalService = Depends(get_release_approval_service),
):
    return to_dict_list(await service.list_for_release(tenant_id, release_id))


@approvals_router.get("/by-release/{release_id}/assert-approved")
async def assert_release_approved(
    release_id: str, tenant_id: str = Depends(get_current_tenant_id), service: ReleaseApprovalService = Depends(get_release_approval_service),
):
    await service.assert_release_approved(tenant_id, release_id)
    return {"release_id": release_id, "approved": True}
