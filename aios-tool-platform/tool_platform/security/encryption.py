"""SecretsEncryptor: real Fernet (AES-128-CBC + HMAC) symmetric
encryption-at-rest for the Credential Vault's `encrypted_payload`.
Keyed off the app's `secret_key` setting via SHA-256 (Fernet requires a
32-byte urlsafe-base64 key; app secret keys are arbitrary-length
strings), so no separate key-management story is needed for this
platform to have real encryption at rest — swapping in a KMS-backed key
later only touches `get_default_encryptor`."""
from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from tool_platform.config.settings import get_settings
from tool_platform.core.exceptions import CredentialError


class SecretsEncryptor:
    def __init__(self, secret_key: str):
        derived_key = base64.urlsafe_b64encode(hashlib.sha256(secret_key.encode("utf-8")).digest())
        self._fernet = Fernet(derived_key)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise CredentialError("cannot decrypt credential — wrong key or corrupted ciphertext") from exc


@lru_cache
def get_default_encryptor() -> SecretsEncryptor:
    return SecretsEncryptor(get_settings().secret_key)
