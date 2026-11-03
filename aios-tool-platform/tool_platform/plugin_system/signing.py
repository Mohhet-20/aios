"""Plugin signing/verification: a plugin's manifest is hashed (SHA-256)
to produce a checksum, and HMAC-signed with the platform's secret key to
produce a signature that proves the checksum wasn't tampered with after
signing. This is deliberately a platform-operated signing scheme (like a
package registry signing its own index), not per-publisher public-key
cryptography — swapping in real publisher-held keys (Ed25519, etc.)
later only touches this one module, not `installation_service.py`,
which just calls `verify_signature`."""
from __future__ import annotations

import hashlib
import hmac
import json


def compute_checksum(manifest: dict) -> str:
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def sign_manifest(manifest: dict, *, secret_key: str) -> tuple[str, str]:
    """Returns (checksum, signature)."""
    checksum = compute_checksum(manifest)
    signature = hmac.new(secret_key.encode("utf-8"), checksum.encode("utf-8"), hashlib.sha256).hexdigest()
    return checksum, signature


def verify_signature(manifest: dict, *, checksum: str, signature: str, secret_key: str) -> bool:
    expected_checksum = compute_checksum(manifest)
    if not hmac.compare_digest(expected_checksum, checksum):
        return False
    expected_signature = hmac.new(secret_key.encode("utf-8"), checksum.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected_signature, signature)
