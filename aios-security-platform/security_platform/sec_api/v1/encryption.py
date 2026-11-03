"""Encryption key lifecycle API: get-or-create the tenant's active
key, and rotate it."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from security_platform.dependencies.dependencies import get_current_tenant_id, get_encryption_key_service
from security_platform.encryption.key_service import EncryptionKeyService
from security_platform.sec_api.serialization import to_dict

router = APIRouter(prefix="/encryption-keys", tags=["encryption"])


@router.get("/active")
async def get_active_key(tenant_id: str = Depends(get_current_tenant_id), service: EncryptionKeyService = Depends(get_encryption_key_service)):
    return to_dict(await service.get_or_create_active_key(tenant_id))


@router.post("/rotate")
async def rotate_key(tenant_id: str = Depends(get_current_tenant_id), service: EncryptionKeyService = Depends(get_encryption_key_service)):
    return to_dict(await service.rotate_key(tenant_id))
