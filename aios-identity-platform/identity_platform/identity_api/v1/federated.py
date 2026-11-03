"""Federated identity linking. The OAuth2/OIDC authorization-code
exchange itself (`OAuth2Provider.exchange_code_for_profile`) needs a
per-organization-configured `ProviderRegistry` and live HTTP client,
which is wired up by whatever hosts this platform (organization-
specific client_id/secret); this router's job starts once that
exchange has already produced a validated `ExternalProfile` — it
provisions-or-logs-in the platform user and manages the link."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from identity_platform.dependencies.dependencies import get_federated_identity_service
from identity_platform.domain.enums import IdentityProviderKey
from identity_platform.federated.federated_identity_service import FederatedIdentityService
from identity_platform.federated.provider import ExternalProfile
from identity_platform.identity_api.serialization import to_dict, to_dict_list

router = APIRouter(prefix="/federated", tags=["federated-identity"])


class ExternalProfileRequest(BaseModel):
    provider_key: IdentityProviderKey
    external_user_id: str
    email: str | None = None
    display_name: str | None = None
    raw_profile: dict = {}


@router.post("/provision-or-login")
async def provision_or_login(body: ExternalProfileRequest, service: FederatedIdentityService = Depends(get_federated_identity_service)):
    profile = ExternalProfile(
        provider_key=body.provider_key, external_user_id=body.external_user_id, email=body.email,
        display_name=body.display_name, raw_profile=body.raw_profile,
    )
    return to_dict(await service.provision_or_login(profile))


@router.get("/users/{user_id}/identities")
async def list_linked_identities(user_id: str, service: FederatedIdentityService = Depends(get_federated_identity_service)):
    return to_dict_list(await service.list_linked_identities(user_id))


@router.delete("/identities/{external_identity_id}", status_code=204)
async def unlink_identity(external_identity_id: str, service: FederatedIdentityService = Depends(get_federated_identity_service)):
    await service.unlink_identity(external_identity_id)
