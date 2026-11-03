import pytest

from memory_platform.security.encryption_service import EncryptionService
from memory_platform.core.exceptions import ValidationError


def test_encrypt_decrypt_roundtrip():
    svc = EncryptionService()
    plaintext = "the quarterly revenue figure is confidential"
    ciphertext = svc.encrypt(plaintext)
    assert ciphertext != plaintext
    assert svc.decrypt(ciphertext) == plaintext


def test_ciphertext_differs_across_calls_but_decrypts_the_same():
    svc = EncryptionService()
    c1 = svc.encrypt("same input")
    c2 = svc.encrypt("same input")
    assert c1 != c2  # Fernet includes a random IV/timestamp
    assert svc.decrypt(c1) == svc.decrypt(c2) == "same input"


def test_empty_string_roundtrips_as_empty():
    svc = EncryptionService()
    assert svc.encrypt("") == ""
    assert svc.decrypt("") == ""


def test_decrypt_invalid_ciphertext_raises():
    svc = EncryptionService()
    with pytest.raises(ValidationError):
        svc.decrypt("not-a-real-fernet-token")


def test_is_encrypted():
    svc = EncryptionService()
    ciphertext = svc.encrypt("secret")
    assert svc.is_encrypted(ciphertext) is True
    assert svc.is_encrypted("plain text") is False


def test_different_secret_keys_cannot_decrypt_each_others_data():
    from memory_platform.config.settings import Settings

    svc_a = EncryptionService(Settings(secret_key="a" * 32))
    svc_b = EncryptionService(Settings(secret_key="b" * 32))
    ciphertext = svc_a.encrypt("tenant-a-only")
    with pytest.raises(ValidationError):
        svc_b.decrypt(ciphertext)
