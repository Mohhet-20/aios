"""Pure license helpers — no DB or service imports. Expiry checking is
a plain datetime comparison; offline license validation signs a
canonical JSON payload with an HMAC secret (reusing
`security.tokens.sign_payload`) so a license file can be verified by
an air-gapped installation with no network call back to this
platform, only the shared secret baked into the installer."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from release_platform.security.tokens import sign_payload
from release_platform.clock import utc_now


def is_expired(expires_at: datetime | None, *, now: datetime | None = None) -> bool:
    if expires_at is None:
        return False
    current = now or utc_now()
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return current >= expires_at


def _canonical_payload(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_license_payload(payload: dict, *, secret: str) -> str:
    return sign_payload(_canonical_payload(payload), secret)


def verify_offline_license(payload: dict, *, signature: str, secret: str) -> bool:
    expected = sign_license_payload(payload, secret=secret)
    return expected == signature
