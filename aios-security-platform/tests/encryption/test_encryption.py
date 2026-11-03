"""Tests for envelope encryption primitives and encryption key
lifecycle (get-or-create, rotation)."""
from __future__ import annotations

import pytest

from security_platform.core.exceptions import DecryptionError
from security_platform.encryption.envelope import decrypt, encrypt
from security_platform.encryption.key_service import EncryptionKeyService

TENANT = "tenant-enc"
MASTER_KEY = "test-master-key-32-bytes-long!!!"


def test_encrypt_decrypt_round_trip():
    ciphertext, nonce = encrypt("super-secret-value", master_key=MASTER_KEY, key_ref="key-ref-1")
    plaintext = decrypt(ciphertext, nonce, master_key=MASTER_KEY, key_ref="key-ref-1")
    assert plaintext == "super-secret-value"


def test_encrypt_output_never_contains_plaintext():
    ciphertext, _ = encrypt("super-secret-value", master_key=MASTER_KEY, key_ref="key-ref-1")
    assert "super-secret-value" not in ciphertext


def test_decrypt_with_wrong_key_ref_raises():
    ciphertext, nonce = encrypt("super-secret-value", master_key=MASTER_KEY, key_ref="key-ref-1")
    with pytest.raises(DecryptionError):
        decrypt(ciphertext, nonce, master_key=MASTER_KEY, key_ref="wrong-ref")


def test_decrypt_tampered_ciphertext_raises():
    ciphertext, nonce = encrypt("super-secret-value", master_key=MASTER_KEY, key_ref="key-ref-1")
    tampered = ciphertext[:-4] + ("AAAA" if not ciphertext.endswith("AAAA") else "BBBB")
    with pytest.raises(DecryptionError):
        decrypt(tampered, nonce, master_key=MASTER_KEY, key_ref="key-ref-1")


@pytest.mark.asyncio
async def test_get_or_create_active_key_is_idempotent(repos):
    service = EncryptionKeyService(repos)
    first = await service.get_or_create_active_key(TENANT)
    second = await service.get_or_create_active_key(TENANT)
    assert first.id == second.id


@pytest.mark.asyncio
async def test_rotate_key_retires_old_key_and_creates_new_active(repos):
    service = EncryptionKeyService(repos)
    original = await service.get_or_create_active_key(TENANT)
    rotated = await service.rotate_key(TENANT)

    assert rotated.id != original.id
    assert rotated.status == "active"

    refreshed_original = await repos.encryption_keys.get(original.id)
    assert refreshed_original.status == "rotated"
    assert refreshed_original.rotated_at is not None

    current_active = await service.get_or_create_active_key(TENANT)
    assert current_active.id == rotated.id
