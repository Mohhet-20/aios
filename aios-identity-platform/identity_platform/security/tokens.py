"""Opaque single-use token primitives shared by every "raw secret, hashed
at rest" flow in the platform — email verification, password reset,
magic links, trusted-device tokens, API keys, webhook secrets, recovery
codes. `generate_raw_token` returns the value that is shown/emailed to
the caller exactly once; only `hash_token`'s output is ever persisted."""
from __future__ import annotations

import hashlib
import secrets


def generate_raw_token(*, num_bytes: int = 32) -> str:
    return secrets.token_urlsafe(num_bytes)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_numeric_code(*, digits: int = 6) -> str:
    """For short-lived human-entered codes (e.g. recovery codes,
    magic-link fallback codes) rather than URL tokens."""
    upper = 10**digits
    return str(secrets.randbelow(upper)).zfill(digits)
