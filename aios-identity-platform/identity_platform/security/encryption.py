"""SecretsEncryptor: real Fernet (AES-128-CBC + HMAC) symmetric
encryption-at-rest for MFA TOTP shared secrets (`MfaFactorModel.
secret_encrypted`) and any other at-rest secret material this platform
needs to decrypt later (unlike password/token hashes, which are
one-way and never decrypted). Keyed off `secret_key` via SHA-256,
exactly mirroring the Tool Platform's Credential Vault encryptor —
swapping in a KMS-backed key later only touches `get_default_encryptor`."""
from __future__ import annotations

import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from identity_platform.config.settings import get_settings
from identity_platform.core.exceptions import MfaError


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
            raise MfaError("cannot decrypt MFA secret — wrong key or corrupted ciphertext") from exc


@lru_cache
def get_default_encryptor() -> SecretsEncryptor:
    return SecretsEncryptor(get_settings().secret_key)
