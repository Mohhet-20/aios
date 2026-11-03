"""Field-level encryption at rest — real symmetric encryption (Fernet:
AES-128-CBC + HMAC-SHA256, authenticated) for sensitive memory/knowledge
content, not a documented-but-unimplemented placeholder. The key is
derived deterministically from `settings.secret_key` via SHA-256 (Fernet
requires a 32-byte urlsafe-base64 key, and `secret_key` is an arbitrary-
length string) — swapping to a real KMS-backed key in production means
replacing `EncryptionService.__init__`'s key derivation, not any caller.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from memory_platform.config.settings import Settings, get_settings
from memory_platform.core.exceptions import ValidationError


def _derive_fernet_key(secret_key: str) -> bytes:
    digest = hashlib.sha256(secret_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class EncryptionService:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._fernet = Fernet(_derive_fernet_key(self.settings.secret_key))

    def encrypt(self, plaintext: str) -> str:
        if plaintext == "":
            return ""
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        if ciphertext == "":
            return ""
        try:
            return self._fernet.decrypt(ciphertext.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise ValidationError("ciphertext is invalid or was encrypted with a different key") from exc

    def is_encrypted(self, value: str) -> bool:
        """Best-effort check — attempts a decrypt without raising."""
        if not value:
            return False
        try:
            self._fernet.decrypt(value.encode("ascii"))
            return True
        except Exception:  # noqa: BLE001
            return False
