"""Generic secret reference issuance/rotation, covering the same
three reference types the schema tracks (webhook secrets, API
credentials, plugin secrets). `material_ref` is always an opaque
`vault://...` pointer — this service refuses to persist anything that
looks like a raw secret was handed to it, enforcing "own the pointer,
not the data" at the write path rather than trusting every caller to
have already opaque-ified their input."""
from __future__ import annotations

import uuid

from developer_platform.core.exceptions import CredentialExposedError, DevSecurityError, NotFoundError, ValidationError
from developer_platform.domain.enums import SecretReferenceType
from developer_platform.models.security import SecretReferenceModel
from developer_platform.repositories.registry import RepositoryRegistry

_VALID_TYPES = {t.value for t in SecretReferenceType}


def _assert_opaque(material_ref: str) -> None:
    if not material_ref.startswith("vault://"):
        raise CredentialExposedError(
            "material_ref must be an opaque vault:// pointer — this platform never stores raw secret material"
        )


class SecretReferenceService:
    def __init__(self, repos: RepositoryRegistry):
        self.repos = repos

    async def issue_reference(self, tenant_id: str, *, name: str, reference_type: str) -> SecretReferenceModel:
        if reference_type not in _VALID_TYPES:
            raise ValidationError(f"'{reference_type}' is not a recognized secret reference type")
        material_ref = f"vault://{reference_type}/{uuid.uuid4().hex}"
        record = SecretReferenceModel(tenant_id=tenant_id, name=name, reference_type=reference_type, material_ref=material_ref)
        return await self.repos.secret_references.add(record)

    async def import_external_reference(self, tenant_id: str, *, name: str, reference_type: str, material_ref: str) -> SecretReferenceModel:
        """Registers a pointer to a secret that already lives in an
        external vault/secrets manager, supplied by the caller rather
        than generated here. `_assert_opaque` is the guard that
        catches a caller accidentally passing the raw secret value
        instead of a reference to it."""
        if reference_type not in _VALID_TYPES:
            raise ValidationError(f"'{reference_type}' is not a recognized secret reference type")
        _assert_opaque(material_ref)
        record = SecretReferenceModel(tenant_id=tenant_id, name=name, reference_type=reference_type, material_ref=material_ref)
        return await self.repos.secret_references.add(record)

    async def rotate_reference(self, reference_id: str) -> SecretReferenceModel:
        record = await self._get_or_404(reference_id)
        record.material_ref = f"vault://{record.reference_type}/{uuid.uuid4().hex}"
        return await self.repos.secret_references.update(record)

    async def get_by_name(self, tenant_id: str, name: str) -> SecretReferenceModel:
        record = await self.repos.secret_references.get_by_name(tenant_id, name)
        if record is None:
            raise DevSecurityError(f"no secret reference named '{name}' for tenant '{tenant_id}'")
        return record

    async def list_by_type(self, tenant_id: str, reference_type: str) -> list[SecretReferenceModel]:
        return await self.repos.secret_references.list_by_type(tenant_id, reference_type)

    async def _get_or_404(self, reference_id: str) -> SecretReferenceModel:
        try:
            return await self.repos.secret_references.get_or_404(reference_id)
        except NotFoundError as exc:
            raise DevSecurityError(f"secret reference '{reference_id}' not found") from exc
