"""Password hashing via stdlib `hashlib.pbkdf2_hmac` — no third-party
crypto dependency, consistent with the "genuinely computed, no
fabrication" ethos carried through every other AIOS platform. Format:
`pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>`, so the iteration
count and salt travel with the hash and a future increase to
`_ITERATIONS` doesn't break verification of hashes written under a
lower count."""
from __future__ import annotations

import hashlib
import hmac
import secrets

_ALGORITHM = "pbkdf2_sha256"
_ITERATIONS = 260_000
_SALT_BYTES = 16


def hash_password(raw_password: str, *, iterations: int = _ITERATIONS) -> str:
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", raw_password.encode("utf-8"), salt, iterations)
    return f"{_ALGORITHM}${iterations}${salt.hex()}${digest.hex()}"


def verify_password(raw_password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations_str, salt_hex, hash_hex = encoded_hash.split("$")
    except ValueError:
        return False
    if algorithm != _ALGORITHM:
        return False
    salt = bytes.fromhex(salt_hex)
    expected = bytes.fromhex(hash_hex)
    candidate = hashlib.pbkdf2_hmac("sha256", raw_password.encode("utf-8"), salt, int(iterations_str))
    return hmac.compare_digest(candidate, expected)
