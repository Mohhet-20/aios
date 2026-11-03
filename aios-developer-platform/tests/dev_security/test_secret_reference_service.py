import uuid

import pytest

from developer_platform.core.exceptions import CredentialExposedError, DevSecurityError, ValidationError
from developer_platform.dev_security.secret_reference_service import SecretReferenceService

def _tid() -> str:
    return f"tenant-{uuid.uuid4().hex[:8]}"


@pytest.mark.asyncio
async def test_issue_reference_produces_opaque_pointer(repos, db_session):
    tenant_id = _tid()
    service = SecretReferenceService(repos)
    ref = await service.issue_reference(tenant_id, name="my-webhook-secret", reference_type="webhook_secret")
    await db_session.commit()
    assert ref.material_ref.startswith("vault://webhook_secret/")


@pytest.mark.asyncio
async def test_issue_reference_invalid_type_raises(repos, db_session):
    service = SecretReferenceService(repos)
    with pytest.raises(ValidationError):
        await service.issue_reference(_tid(), name="x", reference_type="not-a-type")


@pytest.mark.asyncio
async def test_rotate_reference_changes_pointer(repos, db_session):
    tenant_id = _tid()
    service = SecretReferenceService(repos)
    ref = await service.issue_reference(tenant_id, name="rotating-secret", reference_type="api_credential")
    await db_session.commit()
    original_ref = ref.material_ref

    rotated = await service.rotate_reference(ref.id)
    await db_session.commit()
    assert rotated.material_ref != original_ref
    assert rotated.id == ref.id


@pytest.mark.asyncio
async def test_get_by_name_not_found_raises(repos, db_session):
    service = SecretReferenceService(repos)
    with pytest.raises(DevSecurityError):
        await service.get_by_name(_tid(), "does-not-exist")


@pytest.mark.asyncio
async def test_list_by_type(repos, db_session):
    tenant_id = _tid()
    service = SecretReferenceService(repos)
    await service.issue_reference(tenant_id, name="a", reference_type="plugin_secret")
    await service.issue_reference(tenant_id, name="b", reference_type="plugin_secret")
    await db_session.commit()

    refs = await service.list_by_type(tenant_id, "plugin_secret")
    assert len(refs) == 2


@pytest.mark.asyncio
async def test_import_external_reference_rejects_raw_secret(repos, db_session):
    service = SecretReferenceService(repos)
    with pytest.raises(CredentialExposedError):
        await service.import_external_reference(_tid(), name="leaked", reference_type="api_credential", material_ref="sk-live-raw")


@pytest.mark.asyncio
async def test_import_external_reference_accepts_opaque_pointer(repos, db_session):
    tenant_id = _tid()
    service = SecretReferenceService(repos)
    ref = await service.import_external_reference(
        tenant_id, name="external-secret", reference_type="api_credential",
        material_ref="vault://external-provider/abc123",
    )
    await db_session.commit()
    assert ref.material_ref == "vault://external-provider/abc123"


def test_assert_opaque_rejects_non_vault_values():
    from developer_platform.dev_security.secret_reference_service import _assert_opaque

    with pytest.raises(CredentialExposedError):
        _assert_opaque("sk-live-raw-secret-value")
    _assert_opaque("vault://api_credential/abc123")  # does not raise
