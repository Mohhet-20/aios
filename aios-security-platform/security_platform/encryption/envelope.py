"""AES-256-GCM envelope encryption.

DISCLOSED SCOPE BOUNDARY: `EncryptionKeyModel.material_ref` is an
opaque per-key reference (a random token), never the raw key. The
actual 32-byte AES key is derived on demand via PBKDF2-HMAC-SHA256
over the platform's `master_encryption_key` salted with that
reference — so the database never holds key material, only a pointer.
In production, `derive_key_material` is exactly the seam to swap for a
real KMS/HSM call (AWS KMS, GCP KMS, HashiCorp Vault Transit): resolve
`material_ref` against the KMS and get real key bytes back, instead of
deriving them locally from a master key that lives in an env var. That
swap is why the reference/derivation split exists even though this
build's implementation is still "one master secret protects
everything" rather than genuine hardware-backed key isolation."""
from __future__ import annotations

import base64
import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from security_platform.core.exceptions import DecryptionError

_PBKDF2_ITERATIONS = 200_000
_KEY_LEN = 32
_NONCE_LEN = 12


def derive_key_material(master_key: str, key_ref: str) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", master_key.encode("utf-8"), key_ref.encode("utf-8"), _PBKDF2_ITERATIONS, dklen=_KEY_LEN)


def encrypt(plaintext: str, *, master_key: str, key_ref: str) -> tuple[str, str]:
    """Returns (ciphertext_b64, nonce_b64)."""
    key_bytes = derive_key_material(master_key, key_ref)
    nonce = os.urandom(_NONCE_LEN)
    ciphertext = AESGCM(key_bytes).encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.urlsafe_b64encode(ciphertext).decode("ascii"), base64.urlsafe_b64encode(nonce).decode("ascii")


def decrypt(ciphertext_b64: str, nonce_b64: str, *, master_key: str, key_ref: str) -> str:
    key_bytes = derive_key_material(master_key, key_ref)
    try:
        ciphertext = base64.urlsafe_b64decode(ciphertext_b64)
        nonce = base64.urlsafe_b64decode(nonce_b64)
        plaintext = AESGCM(key_bytes).decrypt(nonce, ciphertext, None)
    except Exception as exc:  # noqa: BLE001 — any decrypt failure (bad key, tampered ciphertext, bad nonce) is one condition to callers
        raise DecryptionError("Failed to decrypt value: ciphertext, nonce, or key reference is invalid") from exc
    return plaintext.decode("utf-8")
