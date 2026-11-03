"""ORM <-> domain-aggregate bridge for Credential."""
from __future__ import annotations

from tool_platform.domain.entities import Credential
from tool_platform.domain.enums import CredentialStatus
from tool_platform.models.credential import CredentialModel


def credential_to_domain(model: CredentialModel) -> Credential:
    return Credential(
        id=model.id, workspace_id=model.workspace_id, name=model.name, credential_type=model.credential_type,
        owner_id=model.owner_id, status=CredentialStatus(model.status), expires_at=model.expires_at,
        rotated_at=model.rotated_at,
    )


def apply_credential_domain_to_model(entity: Credential, model: CredentialModel) -> None:
    model.status = entity.status.value
    model.expires_at = entity.expires_at
    model.rotated_at = entity.rotated_at
